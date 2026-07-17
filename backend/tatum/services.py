"""
tatum.services
--------------
Tatum monitoring: address subscriptions and webhook processing.

Tatum is used for MONITORING ONLY.
- It does NOT sign, sweep, or custody any funds.
- It watches HD wallet addresses and fires webhooks when transfers arrive.
"""

import hashlib
import hmac
import json
import logging
import time
from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction as db_transaction
from django.utils import timezone

from .models import TatumAddressSubscription, TatumWebhookEvent

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Chain / subscription type resolution
# ---------------------------------------------------------------------------

# Maps our internal chain key → Tatum chain identifier
CHAIN_TO_TATUM_ID: dict[str, str] = {
    "ethereum": "ethereum-mainnet",
    "bsc": "bsc-mainnet",
    "polygon": "polygon-mainnet",
    "celo": "celo-mainnet",
    "tron": "tron-mainnet",
    "bitcoin": "bitcoin-mainnet",
}


def resolve_tatum_chain_id(chain: str) -> str:
    """Return the Tatum chain identifier for an internal chain key."""
    tatum_chain = CHAIN_TO_TATUM_ID.get(chain.lower().strip())
    if not tatum_chain:
        raise ValidationError(f"No Tatum chain ID mapping for chain '{chain}'")
    return tatum_chain


def resolve_tatum_subscription_type(currency: str, network: str) -> str:
    """
    Determine the Tatum subscription type.
    - ERC-20 / BEP-20 / TRC-20 tokens  → ADDRESS_TOKEN_TRANSACTION
    - Native coins (ETH, BNB, TRX …)   → ADDRESS_TRANSACTION
    """
    # Networks that always use token subscription
    token_networks = {"erc20", "bep20", "trc20", "polygon", "celo"}
    if network.lower() in token_networks:
        return "ADDRESS_TOKEN_TRANSACTION"
    return "ADDRESS_TRANSACTION"


# ---------------------------------------------------------------------------
# Low-level HTTP helper
# ---------------------------------------------------------------------------

MAX_RETRIES = 2
RETRY_DELAY = 2  # seconds


def tatum_request(path: str, *, method: str = "GET", data: dict | None = None) -> dict:
    """
    Make an authenticated request to the Tatum v3 REST API.
    Returns the parsed JSON response dict.
    Raises ValidationError on configuration or HTTP errors.
    """
    if not settings.TATUM_API_KEY:
        raise ValidationError("TATUM_API_KEY is not configured")

    base_url = settings.TATUM_API_BASE_URL.rstrip("/")
    url = f"{base_url}/{path.lstrip('/')}"

    headers = {
        "x-api-key": settings.TATUM_API_KEY,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if method.upper() == "GET":
                resp = requests.get(url, headers=headers, timeout=30)
            elif method.upper() == "POST":
                resp = requests.post(url, headers=headers, json=data or {}, timeout=30)
            elif method.upper() == "DELETE":
                resp = requests.delete(url, headers=headers, timeout=30)
            else:
                resp = requests.request(method, url, headers=headers, json=data or {}, timeout=30)

            logger.debug("Tatum %s %s → %s", method, url, resp.status_code)

            try:
                parsed = resp.json()
            except ValueError:
                if resp.status_code >= 400:
                    return {"ok": False, "status_code": resp.status_code, "error": resp.text}
                parsed = {"ok": True, "raw": resp.text}

            if resp.status_code >= 400:
                error_msg = (
                    parsed.get("message")
                    or parsed.get("error")
                    or str(parsed)
                )
                return {"ok": False, "status_code": resp.status_code, "error": error_msg, "raw": parsed}

            return parsed

        except requests.exceptions.RequestException as exc:
            logger.warning("Tatum %s %s → %s (attempt %d/%d)", method, url, exc, attempt, MAX_RETRIES)
            if attempt < MAX_RETRIES:
                last_error = str(exc)
                time.sleep(RETRY_DELAY)
                continue
            return {"ok": False, "error": str(exc)}

    return {"ok": False, "error": f"Tatum request failed after {MAX_RETRIES} attempts: {last_error}"}


# ---------------------------------------------------------------------------
# Address subscription management
# ---------------------------------------------------------------------------

def create_tatum_address_subscription(hd_address) -> TatumAddressSubscription:
    """
    Subscribe a derived HD address to Tatum monitoring.
    Returns the TatumAddressSubscription record.

    If a subscription already exists and is ACTIVE, it is returned as-is.
    """
    # Return existing active subscription
    existing = TatumAddressSubscription.objects.filter(
        hd_address=hd_address,
        status=TatumAddressSubscription.ACTIVE,
    ).first()
    if existing:
        return existing

    tatum_chain = resolve_tatum_chain_id(hd_address.chain)
    sub_type = resolve_tatum_subscription_type(hd_address.currency, hd_address.network)

    if not settings.TATUM_WEBHOOK_URL:
        raise ValidationError("TATUM_WEBHOOK_URL is not configured")

    payload = {
        "type": sub_type,
        "attr": {
            "chain": tatum_chain,
            "address": hd_address.address,
            "url": settings.TATUM_WEBHOOK_URL,
        },
    }

    response = tatum_request("subscription", method="POST", data=payload)

    if response.get("ok") is False:
        raise ValidationError(
            f"Tatum subscription failed for {hd_address.address}: {response.get('error')}"
        )

    subscription_id = (
        response.get("id")
        or response.get("subscriptionId")
        or response.get("subscription_id")
        or ""
    )
    if not subscription_id:
        raise ValidationError(
            f"Tatum subscription response missing id: {response}"
        )

    subscription, _created = TatumAddressSubscription.objects.update_or_create(
        hd_address=hd_address,
        defaults={
            "tatum_subscription_id": str(subscription_id),
            "address": hd_address.address,
            "chain": tatum_chain,
            "subscription_type": sub_type,
            "status": TatumAddressSubscription.ACTIVE,
            "provider_payload": response,
        },
    )

    logger.info(
        "Tatum subscription created: address=%s chain=%s sub_id=%s",
        hd_address.address, tatum_chain, subscription_id,
    )
    return subscription


def cancel_tatum_address_subscription(subscription: TatumAddressSubscription) -> dict:
    """
    Cancel an active Tatum address subscription.
    Updates the local record to CANCELLED status.
    """
    response = tatum_request(
        f"subscription/{subscription.tatum_subscription_id}",
        method="DELETE",
    )

    subscription.status = TatumAddressSubscription.CANCELLED
    subscription.save(update_fields=["status", "updated_at"])

    logger.info(
        "Tatum subscription cancelled: sub_id=%s address=%s",
        subscription.tatum_subscription_id, subscription.address,
    )
    return response


# ---------------------------------------------------------------------------
# Webhook signature verification
# ---------------------------------------------------------------------------

def verify_tatum_webhook_signature(raw_body: bytes, signature: str | None) -> bool:
    """
    Verify the HMAC-SHA512 signature on an incoming Tatum webhook.
    Tatum signs with TATUM_WEBHOOK_SECRET using HMAC-SHA512.
    Returns True if valid, False otherwise.
    """
    if not settings.TATUM_WEBHOOK_SECRET:
        logger.warning("TATUM_WEBHOOK_SECRET is not configured — skipping signature check")
        return True  # Allow through when secret is not set (dev mode)

    if not signature:
        return False

    expected = hmac.new(
        settings.TATUM_WEBHOOK_SECRET.encode("utf-8"),
        raw_body,
        hashlib.sha512,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


# ---------------------------------------------------------------------------
# Webhook processing
# ---------------------------------------------------------------------------

def _tatum_event_id(payload: dict) -> str:
    """Derive an idempotency key from the Tatum webhook payload."""
    return str(
        payload.get("subscriptionId")
        or payload.get("id")
        or payload.get("txId")
        or payload.get("txHash")
        or hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    )


def _parse_decimal(value, field_name: str) -> Decimal:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise ValidationError(f"Tatum webhook field '{field_name}' is invalid: {value!r}") from exc
    if amount <= 0:
        raise ValidationError(f"Tatum webhook field '{field_name}' must be > 0")
    return amount


@db_transaction.atomic
def process_tatum_webhook(payload: dict, *, signature: str = "") -> dict:
    """
    Entry point for all inbound Tatum webhooks.
    Stores the event for idempotency, then dispatches to the appropriate handler.
    """
    event_id = _tatum_event_id(payload)
    event_type = payload.get("type", "")
    address = (
        payload.get("address")
        or (payload.get("attr") or {}).get("address")
        or ""
    )
    chain = (
        payload.get("chain")
        or (payload.get("attr") or {}).get("chain")
        or ""
    )

    try:
        event = TatumWebhookEvent.objects.create(
            tatum_event_id=event_id,
            event_type=event_type,
            address=address,
            chain=chain,
            signature=signature,
            payload=payload,
        )
    except IntegrityError:
        return {
            "message": "Tatum webhook already processed",
            "event_id": event_id,
            "duplicate": True,
        }

    result = {"message": "Tatum webhook stored", "event_type": event_type, "event_id": event_id}

    try:
        if event_type in ("ADDRESS_TRANSACTION", "ADDRESS_TOKEN_TRANSACTION", "INCOMING_BLOCKCHAIN_TRANSACTION"):
            result = handle_tatum_incoming_transfer(payload)
        else:
            result["ignored"] = True
            result["reason"] = f"Unhandled event type: {event_type}"
    except Exception as exc:
        logger.exception("Error processing Tatum webhook event_id=%s", event_id)
        result["error"] = str(exc)

    event.processed_at = timezone.now()
    event.save(update_fields=["processed_at"])
    return result


def _resolve_sell_intent(user, currency: str, amount: Decimal):
    """
    Return the oldest active PENDING_PAYMENT sell Transaction whose crypto_amount
    matches the incoming deposit exactly, or None if this should be a plain deposit.

    Intent is resolved purely by database state at webhook time — no pre-linked
    OnChainDeposit records are needed. If the user has no active sell session for
    this asset + amount the crypto is treated as a wallet top-up instead.
    """
    from broker.models import Transaction

    return (
        Transaction.objects.select_for_update()
        .filter(
            user=user,
            transaction_type=Transaction.SELL,
            status__in=[Transaction.PENDING_PAYMENT, Transaction.PENDING_REVIEW],
            asset__code=currency,
            crypto_amount=amount,
            expires_at__gt=timezone.now(),
        )
        .order_by("created_at")  # FIFO — oldest active sell wins
        .first()
    )


def handle_tatum_incoming_transfer(payload: dict) -> dict:
    """
    Process an ADDRESS_TRANSACTION or ADDRESS_TOKEN_TRANSACTION event.

    Intent is resolved at detection time:
    - If an active sell Transaction matches the user + currency + amount → SELL
    - Otherwise → plain wallet deposit
    """
    from hd_wallets.models import HdWalletAddress, OnChainDeposit

    address = (
        payload.get("address")
        or payload.get("to")
        or (payload.get("attr") or {}).get("address")
        or ""
    ).lower()

    amount_raw = (
        payload.get("amount")
        or payload.get("value")
        or "0"
    )
    try:
        amount = _parse_decimal(amount_raw, "amount")
    except ValidationError as exc:
        return {"message": "Tatum transfer ignored", "reason": str(exc)}

    txid = (
        payload.get("txId")
        or payload.get("txHash")
        or payload.get("hash")
        or ""
    )
    currency = (payload.get("asset") or payload.get("currency") or "").upper()

    if not address:
        return {"message": "Tatum transfer ignored", "reason": "missing address"}

    # Find the HD address record
    hd_address = HdWalletAddress.objects.filter(
        address__iexact=address,
    ).select_related("user").first()

    if not hd_address:
        logger.warning("Tatum webhook received for unknown address: %s", address)
        return {"message": "Tatum transfer ignored", "reason": f"unknown address: {address}"}

    resolved_currency = currency or hd_address.currency

    # Resolve intent: is there an active sell session waiting for this crypto?
    sell_transaction = _resolve_sell_intent(hd_address.user, resolved_currency, amount)

    deposit = _find_or_create_on_chain_deposit(
        hd_address=hd_address,
        currency=resolved_currency,
        network=hd_address.network,
        amount=amount,
        txid=txid,
        payload=payload,
        broker_transaction=sell_transaction,
    )

    if deposit.credited_at:
        return {
            "message": "Tatum deposit already credited",
            "deposit_id": str(deposit.id),
            "credited": False,
        }

    deposit.status = OnChainDeposit.CREDITED
    deposit.txid = txid
    deposit.provider_payload = payload
    deposit.credited_at = timezone.now()
    deposit.save(update_fields=["status", "txid", "provider_payload", "credited_at", "updated_at"])

    if deposit.broker_transaction_id:
        logger.info(
            "Tatum deposit matched to sell transaction %s — advancing.",
            deposit.broker_transaction_id,
        )
        advance_sell_transaction_from_deposit(deposit)
    else:
        logger.info(
            "Tatum deposit for user=%s currency=%s — no active sell session, crediting wallet.",
            hd_address.user.email, resolved_currency,
        )
        _credit_wallet_for_standalone_deposit(deposit)

    return {
        "message": "Tatum deposit processed",
        "deposit_id": str(deposit.id),
        "currency": deposit.currency,
        "amount": str(amount),
        "intent": "sell" if deposit.broker_transaction_id else "deposit",
        "credited": True,
    }


def _find_or_create_on_chain_deposit(
    *, hd_address, currency, network, amount, txid, payload, broker_transaction=None
):
    """
    Find an existing OnChainDeposit for this txid/currency, or create a new one.
    `broker_transaction` is resolved by the caller via _resolve_sell_intent and
    linked at creation time — no pre-created pending records are needed.
    """
    from hd_wallets.models import OnChainDeposit

    # Prefer an existing match by txid (idempotency)
    if txid:
        existing = OnChainDeposit.objects.select_for_update().filter(
            txid=txid, currency=currency
        ).first()
        if existing:
            # If the existing deposit has no broker_transaction but we now resolved
            # one (e.g. a second webhook retry after the sell session was created),
            # update the link.
            if broker_transaction and not existing.broker_transaction_id:
                existing.broker_transaction = broker_transaction
                existing.save(update_fields=["broker_transaction", "updated_at"])
            return existing

    return OnChainDeposit.objects.create(
        user=hd_address.user,
        wallet_address=hd_address,
        broker_transaction=broker_transaction,
        currency=currency,
        network=network,
        amount=amount,
        txid=txid,
        status=OnChainDeposit.PENDING,
        provider_payload=payload,
    )


def advance_sell_transaction_from_deposit(deposit) -> None:
    """
    Advance a broker sell transaction from PENDING_PAYMENT → COMPLETED
    when the corresponding on-chain deposit arrives.
    """
    from broker.models import Transaction
    from broker.services import transition_transaction

    transaction_obj = deposit.broker_transaction
    if not transaction_obj:
        return

    if transaction_obj.status == Transaction.PENDING_PAYMENT:
        transition_transaction(transaction_obj, Transaction.PAID, note="On-chain deposit received via Tatum")
        transition_transaction(transaction_obj, Transaction.PROCESSING, note="Auto-processing HD wallet sell")
        transition_transaction(transaction_obj, Transaction.COMPLETED, note="Auto-completed HD wallet sell")
        return

    # Late arrival: crypto arrived after transaction expired
    if transaction_obj.status == Transaction.FAILED and transaction_obj.fail_reason == "expired":
        logger.warning(
            "Late Tatum deposit for expired transaction %s — re-opening.",
            transaction_obj.id,
        )
        transaction_obj.status = Transaction.PENDING_PAYMENT
        transaction_obj.fail_reason = ""
        transaction_obj.failed_at = None
        transaction_obj.save(update_fields=["status", "fail_reason", "failed_at"])
        transition_transaction(transaction_obj, Transaction.PAID, note="Late on-chain deposit — transaction re-opened")
        transition_transaction(transaction_obj, Transaction.PROCESSING, note="Auto-processing late HD wallet sell")
        transition_transaction(transaction_obj, Transaction.COMPLETED, note="Auto-completed late HD wallet sell")
        return

    logger.info(
        "Skipping sell advance for transaction %s — status: %s",
        transaction_obj.id, transaction_obj.status,
    )


def _credit_wallet_for_standalone_deposit(deposit) -> None:
    """
    Credit the user's in-app wallet when a Tatum deposit has no linked
    broker sell transaction (i.e. a plain wallet top-up).
    """
    from rates.models import Asset
    from wallets.models import PlatformReserve, ReserveMovement
    from wallets.services import deposit_to_wallet

    asset = Asset.objects.filter(code=deposit.currency, is_active=True).first()
    if not asset:
        logger.warning("Unsupported Tatum deposit currency: %s", deposit.currency)
        return

    deposit_to_wallet(
        deposit.user,
        asset,
        deposit.amount,
        notes=f"Tatum on-chain deposit {deposit.txid or deposit.id}",
    )

    reserve, _ = PlatformReserve.objects.get_or_create(asset=asset)
    reserve.balance += deposit.amount
    reserve.save(update_fields=["balance", "updated_at"])
    ReserveMovement.objects.create(
        asset=asset,
        movement_type=ReserveMovement.IN,
        amount=deposit.amount,
        notes=f"Tatum deposit {deposit.txid or deposit.id}",
    )


# ---------------------------------------------------------------------------
# Treasury balance (used by hd_wallets.services)
# ---------------------------------------------------------------------------

def get_tatum_treasury_balance(*, currency: str, network: str) -> Decimal:
    """
    Fetch the treasury master wallet balance for a currency/network via Tatum.
    """
    from hd_wallets.services import CHAIN_MASTER_ADDRESS_SETTING, resolve_chain

    chain = resolve_chain(network)
    master_address_setting = CHAIN_MASTER_ADDRESS_SETTING.get(chain, "")
    master_address = getattr(settings, master_address_setting, "") if master_address_setting else ""

    if not master_address:
        raise ValidationError(
            f"Master wallet address for chain '{chain}' is not configured."
        )

    tatum_chain = resolve_tatum_chain_id(chain)
    response = tatum_request(f"{tatum_chain}/account/balance/{master_address}")

    if response.get("ok") is False:
        raise ValidationError(
            f"Tatum balance fetch failed for {master_address}: {response.get('error')}"
        )

    raw_balance = (
        response.get("balance")
        or response.get("availableBalance")
        or "0"
    )
    try:
        return Decimal(str(raw_balance))
    except InvalidOperation:
        return Decimal("0")


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------

def get_tatum_diagnostics() -> dict:
    """Return health-check info about the Tatum integration."""
    active_count = TatumAddressSubscription.objects.filter(
        status=TatumAddressSubscription.ACTIVE
    ).count()
    cancelled_count = TatumAddressSubscription.objects.filter(
        status=TatumAddressSubscription.CANCELLED
    ).count()
    failed_count = TatumAddressSubscription.objects.filter(
        status=TatumAddressSubscription.FAILED
    ).count()

    api_reachable = False
    api_error = ""
    try:
        resp = tatum_request("subscription?pageSize=1")
        api_reachable = resp.get("ok") is not False
        if not api_reachable:
            api_error = str(resp.get("error", ""))
    except Exception as exc:
        api_error = str(exc)

    return {
        "configured": bool(settings.TATUM_API_KEY and settings.TATUM_WEBHOOK_SECRET),
        "webhook_url": settings.TATUM_WEBHOOK_URL,
        "api_reachable": api_reachable,
        "api_error": api_error,
        "subscriptions": {
            "active": active_count,
            "cancelled": cancelled_count,
            "failed": failed_count,
        },
    }
