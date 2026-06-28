import hashlib
import hmac
import json
import logging
import time
from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import QuidaxDeposit, QuidaxSubAccount, QuidaxWalletAddress, QuidaxWebhookEvent

logger = logging.getLogger(__name__)

MAX_RETRIES = 2
RETRY_DELAY = 2  # seconds


def _json_decimal_default(value):
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _quidax_request(path: str, *, params: dict | None = None, data: dict | None = None, method: str = "GET") -> dict:
    if not settings.QUIDAX_API_KEY:
        raise ValidationError("Quidax API key is not configured")

    base_url = settings.QUIDAX_API_BASE_URL.rstrip("/")
    url = f"{base_url}/{path.lstrip('/')}"

    headers = {
        "Authorization": f"Bearer {settings.QUIDAX_API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, params=params, timeout=30)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, params=params, json=data, timeout=30)
            else:
                response = requests.request(method, url, headers=headers, params=params, json=data, timeout=30)
            
            logger.debug("Quidax %s %s -> %s", method, url, response.status_code)
            
            # Handle successful responses and JSON-formatted error responses
            try:
                parsed = response.json()
            except ValueError:
                # If we can't parse JSON, it might be a Cloudflare HTML error page
                if response.status_code >= 400:
                    if response.status_code == 503 and attempt < MAX_RETRIES:
                        last_error = response.text
                        time.sleep(RETRY_DELAY)
                        continue
                    return {"ok": False, "status_code": response.status_code, "error": response.text}
                # Non-JSON success body (shouldn't happen with Quidax)
                parsed = {"ok": True, "raw": response.text}

            # Even if it's 4xx or 5xx, Quidax usually returns a JSON error structure
            if response.status_code >= 400:
                error_message = parsed.get("message") or parsed.get("error") or str(parsed)
                return {"ok": False, "status_code": response.status_code, "error": error_message, "raw": parsed}

            return parsed

        except requests.exceptions.RequestException as exc:
            logger.warning("Quidax %s %s -> %s (attempt %d/%d)", method, url, exc, attempt, MAX_RETRIES)
            if attempt < MAX_RETRIES:
                last_error = str(exc)
                time.sleep(RETRY_DELAY)
                continue
            return {"ok": False, "error": str(exc)}

    return {"ok": False, "error": f"Quidax request failed after {MAX_RETRIES} attempts: {last_error}"}


def _provider_data(response: dict) -> dict:
    data = response.get("data")
    return data if isinstance(data, dict) else response


def _check_quidax_response(response: dict, operation: str) -> None:
    """Raise ValidationError if Quidax returned an error."""
    if response.get("ok") is False:
        raise ValidationError(f"Quidax {operation} failed: {response.get('error')}")
    status = response.get("status")
    if isinstance(status, str) and status.lower() == "error":
        message = response.get("message") or response.get("error") or "Unknown error"
        raise ValidationError(f"Quidax {operation} failed: {message}")


def _clean_name(name: str, fallback: str) -> str:
    cleaned = "".join(c for c in (name or "") if c.isalpha())
    return cleaned if cleaned else fallback

def _sub_account_payload(user) -> dict:
    return {
        "email": user.email,
        "first_name": _clean_name(getattr(user, "first_name", ""), "CheeseBall"),
        "last_name": _clean_name(getattr(user, "last_name", ""), "User"),
    }


def ensure_sub_account(user) -> QuidaxSubAccount:
    existing = QuidaxSubAccount.objects.filter(user=user).first()
    if existing:
        return existing

    payload = _sub_account_payload(user)
    response = _quidax_request("users", data=payload, method="POST")

    if response.get("ok") is False and "already exists" in str(response.get("error", "")).lower():
        import secrets
        parts = user.email.split("@")
        if len(parts) == 2:
            payload["email"] = f"{parts[0]}+{secrets.token_hex(4)}@{parts[1]}"
        else:
            payload["email"] = f"{user.email}+{secrets.token_hex(4)}@cheeseball.internal"
        response = _quidax_request("users", data=payload, method="POST")

    _check_quidax_response(response, "sub-account creation")

    data = _provider_data(response)
    quidax_id = data.get("id") or data.get("uuid") or data.get("user_id")
    if not quidax_id:
        raise ValidationError(f"Quidax sub-account creation did not return a user id: {response}")

    account, _created = QuidaxSubAccount.objects.update_or_create(
        user=user,
        defaults={
            "quidax_id": str(quidax_id),
            "email": data.get("email") or payload["email"],
            "provider_payload": response,
        },
    )
    return account


def ensure_wallet_address(user, *, currency: str, network: str = "") -> QuidaxWalletAddress:
    currency = currency.upper().strip()
    # Normalise to lowercase – Quidax expects e.g. "trc20", not "TRC20".
    network = (network or "").strip().lower()
    existing = QuidaxWalletAddress.objects.filter(user=user, currency=currency, network=network).first()
    if existing and existing.status == QuidaxWalletAddress.GENERATED and existing.address:
        return existing

    account = ensure_sub_account(user)
    response = _quidax_request(
        f"users/{account.quidax_id}/wallets/{currency.lower()}/addresses",
        params=None,
        data={"network": network} if network else {},
        method="POST",
    )
    _check_quidax_response(response, "wallet address generation")

    data = _provider_data(response)
    address = data.get("address") or data.get("wallet_address") or ""
    destination_tag = data.get("destination_tag") or data.get("memo") or data.get("tag") or ""
    status = QuidaxWalletAddress.GENERATED if address else QuidaxWalletAddress.PENDING

    wallet_address, _created = QuidaxWalletAddress.objects.update_or_create(
        user=user,
        currency=currency,
        network=network,
        defaults={
            "sub_account": account,
            "address": address,
            "destination_tag": destination_tag,
            "status": status,
            "provider_payload": response,
        },
    )
    return wallet_address


def get_wallet_balance(user, currency: str) -> dict:
    account = ensure_sub_account(user)
    response = _quidax_request(f"users/{account.quidax_id}/wallets/{currency.lower()}")
    _check_quidax_response(response, "wallet balance fetch")

    data = _provider_data(response)
    return {
        "currency": data.get("currency", currency).upper(),
        "balance": str(data.get("balance", "0")),
        "locked": str(data.get("locked", "0")),
        "staked": str(data.get("staked", "0")),
    }


def initiate_crypto_withdrawal(user, *, currency: str, amount, fund_uid: str, network: str = "") -> dict:
    currency = currency.lower().strip()
    network = (network or "").strip()
    
    payload = {
        "currency": currency,
        "amount": str(amount),
        "fund_uid": fund_uid,
    }
    if network:
        payload["network"] = network

    # We use "me" because the platform's main wallet holds the liquidity.
    response = _quidax_request("users/me/withdraws", data=payload, method="POST")
    _check_quidax_response(response, "crypto withdrawal")
    
    return _provider_data(response)


def sweep_sub_account_to_merchant(quidax_user_id: str, *, currency: str, merchant_address: str, network: str = "", min_amount: str = "0.0001") -> dict:
    """
    Sweeps available balance of a given currency from a Quidax sub-account
    to the merchant's main wallet address.

    Returns a dict summarising what happened:
      { "swept": bool, "amount": str, "currency": str, "response": dict | None, "reason": str }
    """
    from decimal import Decimal, InvalidOperation

    currency_lower = currency.lower().strip()
    currency_upper = currency.upper().strip()

    # 1. Fetch the sub-account's balance
    balance_response = _quidax_request(f"users/{quidax_user_id}/wallets/{currency_lower}")
    if balance_response.get("ok") is False:
        return {"swept": False, "currency": currency_upper, "amount": "0", "reason": f"balance fetch failed: {balance_response.get('error')}", "response": None}

    data = _provider_data(balance_response)
    try:
        available = Decimal(str(data.get("balance", "0")))
    except (InvalidOperation, TypeError):
        available = Decimal("0")

    logger.info("Sweep check: sub-account %s has %s %s available", quidax_user_id, available, currency_upper)

    try:
        minimum = Decimal(str(min_amount))
    except (InvalidOperation, TypeError):
        minimum = Decimal("0.0001")

    if available <= minimum:
        return {
            "swept": False,
            "currency": currency_upper,
            "amount": str(available),
            "reason": f"balance {available} is at or below minimum sweep threshold {minimum}",
            "response": None,
        }

    # 2. Initiate withdrawal from the sub-account to the merchant address
    payload: dict = {
        "currency": currency_lower,
        "amount": str(available),
        "fund_uid": merchant_address,
    }
    if network:
        payload["network"] = network

    withdraw_response = _quidax_request(
        f"users/{quidax_user_id}/withdraws",
        data=payload,
        method="POST",
    )

    if withdraw_response.get("ok") is False:
        return {
            "swept": False,
            "currency": currency_upper,
            "amount": str(available),
            "reason": f"withdrawal failed: {withdraw_response.get('error')}",
            "response": withdraw_response,
        }

    logger.info("Sweep sent: %s %s from sub-account %s -> %s", available, currency_upper, quidax_user_id, merchant_address)
    return {
        "swept": True,
        "currency": currency_upper,
        "amount": str(available),
        "reason": "sweep initiated successfully",
        "response": _provider_data(withdraw_response),
    }


def sweep_all_sub_accounts_to_merchant(*, currencies: list[str], merchant_addresses: dict[str, str], networks: dict[str, str] | None = None, min_amount: str = "0.0001") -> list[dict]:
    """
    Sweeps all known sub-accounts in the database for the given currencies.

    merchant_addresses: { "USDT": "0xABC...", "BTC": "bc1q...", ... }
    networks:           { "USDT": "trc20", ... }  (optional, per-currency)

    Returns a list of result dicts from sweep_sub_account_to_merchant.
    """
    from .models import QuidaxSubAccount

    networks = networks or {}
    results = []

    sub_accounts = QuidaxSubAccount.objects.select_related("user").all()
    logger.info("Sweeping %d sub-account(s) for currencies: %s", sub_accounts.count(), currencies)

    for sub in sub_accounts:
        for currency in currencies:
            currency_upper = currency.upper()
            merchant_address = merchant_addresses.get(currency_upper, "")
            if not merchant_address:
                results.append({
                    "swept": False,
                    "quidax_user_id": sub.quidax_id,
                    "user": sub.user.email,
                    "currency": currency_upper,
                    "amount": "0",
                    "reason": f"no merchant address configured for {currency_upper}",
                    "response": None,
                })
                continue

            result = sweep_sub_account_to_merchant(
                sub.quidax_id,
                currency=currency_upper,
                merchant_address=merchant_address,
                network=networks.get(currency_upper, ""),
                min_amount=min_amount,
            )
            result["quidax_user_id"] = sub.quidax_id
            result["user"] = sub.user.email
            results.append(result)

    return results


def create_pending_sell_deposit(*, transaction_obj, wallet_address: QuidaxWalletAddress) -> QuidaxDeposit:
    return QuidaxDeposit.objects.create(
        user=transaction_obj.user,
        sub_account=wallet_address.sub_account,
        wallet_address=wallet_address,
        broker_transaction=transaction_obj,
        currency=transaction_obj.asset.code.upper(),
        network=transaction_obj.network,
        amount=transaction_obj.crypto_amount,
        status=QuidaxDeposit.PENDING,
        provider_payload={"source": "broker_sell"},
    )


def verify_webhook_signature(raw_body: bytes, signature: str | None, timestamp: str | None = None) -> bool:
    if not settings.QUIDAX_WEBHOOK_SECRET:
        raise ValidationError("Quidax webhook secret is not configured")
    if not signature:
        return False

    body = raw_body.decode("utf-8")
    signing_payloads = [body]
    if timestamp:
        signing_payloads.insert(0, f"{timestamp}.{body}")

    for payload in signing_payloads:
        digest = hmac.new(
            settings.QUIDAX_WEBHOOK_SECRET.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if hmac.compare_digest(digest, signature):
            return True
    return False


def _event_type(payload: dict) -> str:
    return payload.get("event") or payload.get("type") or payload.get("event_type") or ""


def _event_id(payload: dict) -> str:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    return str(
        payload.get("id")
        or payload.get("event_id")
        or data.get("id")
        or data.get("reference")
        or data.get("txid")
        or hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    )


def _deep_get(payload: dict, *paths):
    for path in paths:
        current = payload
        for key in path:
            if not isinstance(current, dict):
                current = None
                break
            current = current.get(key)
        if current not in (None, ""):
            return current
    return None


def _decimal(value, field_name: str) -> Decimal:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise ValidationError(f"Quidax webhook {field_name} is invalid") from exc
    if amount <= 0:
        raise ValidationError(f"Quidax webhook {field_name} must be greater than zero")
    return amount


@transaction.atomic
def process_webhook(payload: dict, *, signature: str = "") -> dict:
    event_type = _event_type(payload)
    event_id = _event_id(payload)

    try:
        event = QuidaxWebhookEvent.objects.create(
            event_type=event_type,
            provider_event_id=event_id,
            signature=signature or "",
            payload=payload,
        )
    except IntegrityError:
        return {"message": "Quidax webhook already processed", "event_id": event_id, "duplicate": True}

    result = {"message": "Quidax webhook stored", "event_type": event_type, "event_id": event_id}
    if event_type == "wallet.address.generated":
        result = _process_wallet_address_generated(payload)
    elif event_type == "deposit.successful":
        result = _process_deposit_successful(payload)
    else:
        result["ignored"] = True

    event.processed_at = timezone.now()
    event.save(update_fields=["processed_at"])
    return result


def _process_wallet_address_generated(payload: dict) -> dict:
    quidax_user_id = str(_deep_get(payload, ("data", "user", "id"), ("data", "user_id")) or "")
    currency = str(_deep_get(payload, ("data", "currency"), ("data", "wallet", "currency")) or "").upper()
    network = str(_deep_get(payload, ("data", "network"), ("data", "address", "network")) or "")
    address = str(_deep_get(payload, ("data", "address"), ("data", "wallet_address"), ("data", "address", "address")) or "")
    destination_tag = str(_deep_get(payload, ("data", "destination_tag"), ("data", "memo"), ("data", "tag")) or "")

    if not (quidax_user_id and currency and address):
        return {"message": "Quidax address webhook ignored", "reason": "missing user, currency, or address"}

    sub_account = QuidaxSubAccount.objects.filter(quidax_id=quidax_user_id).select_related("user").first()
    if not sub_account:
        return {"message": "Quidax address webhook ignored", "reason": "unknown sub-account"}

    wallet_address, _created = QuidaxWalletAddress.objects.update_or_create(
        user=sub_account.user,
        currency=currency,
        network=network,
        defaults={
            "sub_account": sub_account,
            "address": address,
            "destination_tag": destination_tag,
            "status": QuidaxWalletAddress.GENERATED,
            "provider_payload": payload,
        },
    )

    from broker.models import Transaction

    Transaction.objects.filter(
        user=sub_account.user,
        asset_id=currency,
        transaction_type=Transaction.SELL,
        status=Transaction.PENDING_PAYMENT,
        broker_wallet_address="",
    ).update(broker_wallet_address=wallet_address.address)

    return {"message": "Quidax wallet address generated", "currency": currency, "address": wallet_address.address}


def _process_deposit_successful(payload: dict) -> dict:
    quidax_user_id = str(_deep_get(payload, ("data", "user", "id"), ("data", "user_id"), ("data", "account", "id")) or "")
    currency = str(_deep_get(payload, ("data", "currency"), ("data", "wallet", "currency")) or "").upper()
    network = str(_deep_get(payload, ("data", "network"), ("data", "wallet", "network")) or "")
    txid = str(_deep_get(payload, ("data", "txid"), ("data", "transaction_id"), ("data", "hash")) or "")
    provider_reference = str(_deep_get(payload, ("data", "id"), ("data", "reference")) or "")
    amount = _decimal(_deep_get(payload, ("data", "amount"), ("data", "value")), "amount")

    sub_account = QuidaxSubAccount.objects.filter(quidax_id=quidax_user_id).select_related("user").first()
    if not sub_account:
        raise ValidationError("Quidax deposit references an unknown sub-account")
    if not currency:
        raise ValidationError("Quidax deposit currency is missing")

    deposit = _find_or_create_deposit(
        user=sub_account.user,
        sub_account=sub_account,
        currency=currency,
        network=network,
        amount=amount,
        txid=txid,
        provider_reference=provider_reference,
        payload=payload,
    )
    if deposit.credited_at:
        return {"message": "Quidax deposit already credited", "deposit_id": str(deposit.id), "credited": False}

    deposit.status = QuidaxDeposit.SUCCESSFUL
    deposit.amount = amount
    deposit.txid = txid
    deposit.provider_reference = provider_reference
    deposit.provider_payload = payload
    deposit.credited_at = timezone.now()
    deposit.save(update_fields=["status", "amount", "txid", "provider_reference", "provider_payload", "credited_at", "updated_at"])

    from rates.models import Asset

    asset = Asset.objects.filter(code=currency, is_active=True).first()
    if not asset:
        raise ValidationError(f"Unsupported Quidax deposit currency: {currency}")

    if deposit.broker_transaction_id:
        _try_advance_sell_transaction(deposit)
    else:
        from wallets.models import PlatformReserve, ReserveMovement
        from wallets.services import deposit_to_wallet

        deposit_to_wallet(sub_account.user, asset, amount, notes=f"Quidax deposit {txid or provider_reference}")
        reserve, _created = PlatformReserve.objects.get_or_create(asset=asset)
        reserve.balance += amount
        reserve.save(update_fields=["balance", "updated_at"])
        ReserveMovement.objects.create(
            asset=asset,
            movement_type=ReserveMovement.IN,
            amount=amount,
            notes=f"Quidax deposit {txid or provider_reference}",
        )

    return {
        "message": "Quidax deposit processed",
        "deposit_id": str(deposit.id),
        "asset": asset.code,
        "amount": str(amount),
        "credited": True,
    }


def _find_or_create_deposit(*, user, sub_account, currency, network, amount, txid, provider_reference, payload):
    existing = None
    if txid:
        existing = QuidaxDeposit.objects.select_for_update().filter(txid=txid, currency=currency).first()
    if not existing and provider_reference:
        existing = QuidaxDeposit.objects.select_for_update().filter(provider_reference=provider_reference).first()
    if existing:
        return existing

    pending = (
        QuidaxDeposit.objects.select_for_update()
        .filter(user=user, currency=currency, status=QuidaxDeposit.PENDING, amount=amount)
        .order_by("created_at")
        .first()
    )
    if pending:
        pending.txid = txid
        pending.provider_reference = provider_reference
        pending.provider_payload = payload
        pending.network = pending.network or network
        pending.save(update_fields=["txid", "provider_reference", "provider_payload", "network", "updated_at"])
        return pending

    return QuidaxDeposit.objects.create(
        user=user,
        sub_account=sub_account,
        currency=currency,
        network=network,
        amount=amount,
        txid=txid,
        provider_reference=provider_reference,
        status=QuidaxDeposit.PENDING,
        provider_payload=payload,
    )


def _try_advance_sell_transaction(deposit: QuidaxDeposit) -> None:
    if not deposit.broker_transaction_id:
        return

    from broker.models import Transaction
    from broker.services import transition_transaction

    transaction_obj = deposit.broker_transaction
    if transaction_obj.status != Transaction.PENDING_PAYMENT:
        return

    transition_transaction(transaction_obj, Transaction.PAID, note="Quidax deposit received")
    transition_transaction(transaction_obj, Transaction.PROCESSING, note="Auto-processing Quidax external wallet sell")
    transition_transaction(transaction_obj, Transaction.COMPLETED, note="Auto-completed Quidax external wallet sell")


def get_quidax_diagnostics() -> dict:
    return {
        "configured": bool(settings.QUIDAX_API_KEY and settings.QUIDAX_WEBHOOK_SECRET),
        "base_url": settings.QUIDAX_API_BASE_URL,
        "user": _quidax_request("users/me"),
    }
