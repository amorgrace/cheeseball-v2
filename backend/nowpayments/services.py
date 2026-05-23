import hashlib
import hmac
import json
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import CustodyAccount, CustodyDeposit


def _canonical_ipn_payload(payload: dict) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def verify_ipn_signature(payload: dict, signature: str | None) -> bool:
    if not settings.NOWPAYMENTS_IPN_SECRET:
        raise ValidationError("NOWPayments IPN secret is not configured")
    if not signature:
        return False

    digest = hmac.new(
        settings.NOWPAYMENTS_IPN_SECRET.encode("utf-8"),
        _canonical_ipn_payload(payload),
        hashlib.sha512,
    ).hexdigest()
    return hmac.compare_digest(digest, signature)


def _json_decimal_default(value):
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _nowpayments_request(
    path: str,
    *,
    params: dict | None = None,
    data: dict | None = None,
    method: str = "GET",
    bearer_token: str | None = None,
) -> dict:
    if not settings.NOWPAYMENTS_API_KEY:
        raise ValidationError("NOWPayments API key is not configured")

    base_url = settings.NOWPAYMENTS_API_BASE_URL.rstrip("/")
    url = f"{base_url}/{path.lstrip('/')}"
    if params:
        url = f"{url}?{urlencode(params)}"

    body = None
    headers = {
        "x-api-key": settings.NOWPAYMENTS_API_KEY,
        "User-Agent": "CheeseBall/1.0 (+https://cheeseballapp.com)",
    }
    if data is not None:
        body = json.dumps(data, default=_json_decimal_default).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"

    request = Request(
        url,
        data=body,
        headers=headers,
        method=method,
    )

    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return {"ok": False, "status_code": exc.code, "error": body}
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": str(exc)}


def authenticate_nowpayments() -> str:
    if not settings.NOWPAYMENTS_EMAIL or not settings.NOWPAYMENTS_PASSWORD:
        raise ValidationError("NOWPayments email/password are not configured")

    base_url = settings.NOWPAYMENTS_API_BASE_URL.rstrip("/")
    request = Request(
        f"{base_url}/auth",
        data=json.dumps(
            {
                "email": settings.NOWPAYMENTS_EMAIL,
                "password": settings.NOWPAYMENTS_PASSWORD,
            }
        ).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise ValidationError(f"NOWPayments auth failed: {body}") from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ValidationError("Unable to authenticate with NOWPayments") from exc

    token = result.get("token")
    if not token:
        raise ValidationError("NOWPayments auth did not return a token")
    return token


def _sub_partner_name(user) -> str:
    return f"cb-{str(user.id).replace('-', '')[:27]}"[:30]


def ensure_custody_account(user) -> CustodyAccount:
    existing = CustodyAccount.objects.filter(user=user).first()
    if existing:
        return existing

    token = authenticate_nowpayments()
    name = _sub_partner_name(user)
    response = _nowpayments_request(
        "sub-partner/balance",
        data={"name": name},
        method="POST",
        bearer_token=token,
    )
    sub_partner_id = response.get("id") or response.get("sub_partner_id") or response.get("subPartnerId")
    if not sub_partner_id:
        raise ValidationError(f"NOWPayments custody account was not created: {response}")

    account, _created = CustodyAccount.objects.update_or_create(
        user=user,
        defaults={
            "sub_partner_id": str(sub_partner_id),
            "name": response.get("name") or name,
            "provider_payload": response,
        },
    )
    return account


def get_custody_balance(user) -> dict:
    account = ensure_custody_account(user)
    token = authenticate_nowpayments()
    return _nowpayments_request(
        f"sub-partner/balance/{account.sub_partner_id}",
        bearer_token=token,
    )


def create_custody_deposit(user, *, currency: str, amount) -> CustodyDeposit:
    account = ensure_custody_account(user)
    try:
        decimal_amount = Decimal(str(amount))
    except InvalidOperation as exc:
        raise ValidationError("Deposit amount must be a valid number") from exc
    if decimal_amount <= 0:
        raise ValidationError("Deposit amount must be greater than zero")

    token = authenticate_nowpayments()
    response = _nowpayments_request(
        "sub-partner/payment",
        data={
            "currency": currency.lower(),
            "amount": decimal_amount,
            "sub_partner_id": account.sub_partner_id,
        },
        method="POST",
        bearer_token=token,
    )
    if response.get("ok") is False:
        raise ValidationError(f"NOWPayments custody deposit failed: {response.get('error')}")

    pay_amount = response.get("pay_amount")
    deposit = CustodyDeposit.objects.create(
        user=user,
        custody_account=account,
        currency=currency.lower(),
        amount=decimal_amount,
        provider_payment_id=str(response.get("payment_id") or response.get("id") or ""),
        pay_address=response.get("pay_address") or "",
        pay_amount=Decimal(str(pay_amount)) if pay_amount is not None else None,
        payment_status=response.get("payment_status") or CustodyDeposit.PENDING,
        provider_payload=response,
    )
    return deposit


@transaction.atomic
def process_custody_ipn(payload: dict) -> dict:
    payment_id = str(payload.get("payment_id") or payload.get("id") or "")
    if not payment_id:
        return {"message": "NOWPayments IPN ignored", "reason": "missing payment_id"}

    deposit = (
        CustodyDeposit.objects.select_for_update()
        .select_related("custody_account", "user")
        .filter(provider_payment_id=payment_id)
        .first()
    )
    if not deposit:
        return {"message": "NOWPayments IPN ignored", "reason": "unknown payment"}

    status = payload.get("payment_status") or payload.get("status") or deposit.payment_status
    deposit.payment_status = status
    deposit.provider_payload = payload

    if status != CustodyDeposit.FINISHED:
        deposit.save(update_fields=["payment_status", "provider_payload", "updated_at"])
        return {
            "message": "NOWPayments IPN processed",
            "payment_id": payment_id,
            "payment_status": status,
            "credited": False,
        }

    if deposit.credited_at:
        deposit.save(update_fields=["payment_status", "provider_payload", "updated_at"])
        return {
            "message": "NOWPayments IPN processed",
            "payment_id": payment_id,
            "payment_status": status,
            "credited": False,
            "already_credited": True,
        }

    amount = payload.get("actually_paid") or payload.get("pay_amount") or deposit.pay_amount or deposit.amount
    try:
        credit_amount = Decimal(str(amount))
    except InvalidOperation as exc:
        raise ValidationError("NOWPayments IPN amount is invalid") from exc
    if credit_amount <= 0:
        raise ValidationError("NOWPayments IPN amount must be greater than zero")

    currency = (payload.get("pay_currency") or deposit.currency).upper()
    from rates.models import Asset
    from wallets.models import PlatformReserve, ReserveMovement
    from wallets.services import deposit_to_wallet

    asset = Asset.objects.filter(code=currency, is_active=True).first()
    if not asset:
        raise ValidationError(f"Unsupported NOWPayments custody currency: {currency}")

    deposit_to_wallet(deposit.user, asset, credit_amount, notes=f"NOWPayments custody deposit {payment_id}")

    platform_reserve, _created = PlatformReserve.objects.get_or_create(asset=asset)
    platform_reserve.balance += credit_amount
    platform_reserve.save(update_fields=["balance", "updated_at"])
    ReserveMovement.objects.create(
        asset=asset,
        movement_type=ReserveMovement.IN,
        amount=credit_amount,
        notes=f"NOWPayments custody deposit {payment_id}",
    )

    deposit.credited_at = timezone.now()
    deposit.pay_amount = credit_amount
    deposit.save(update_fields=["payment_status", "provider_payload", "pay_amount", "credited_at", "updated_at"])
    return {
        "message": "NOWPayments IPN processed",
        "payment_id": payment_id,
        "payment_status": status,
        "credited": True,
        "asset": asset.code,
        "amount": str(credit_amount),
    }


def get_nowpayments_diagnostics() -> dict:
    status = _nowpayments_request("status")
    currencies = _nowpayments_request("currencies")
    balance = _nowpayments_request("balance")
    return {
        "configured": bool(settings.NOWPAYMENTS_API_KEY and settings.NOWPAYMENTS_IPN_SECRET),
        "status": status,
        "currencies": currencies,
        "balance": balance,
    }
