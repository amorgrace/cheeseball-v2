from django.core.exceptions import ValidationError
from ninja.responses import Response

from .services import (
    ensure_sub_account,
    ensure_wallet_address,
    get_quidax_diagnostics,
    get_wallet_balance,
    process_webhook,
    verify_webhook_signature,
)


def _error_message(exc: ValidationError) -> str:
    """Extract a clean error string from a Django ValidationError."""
    if hasattr(exc, "messages") and exc.messages:
        return exc.messages[0]
    return str(exc)


def webhook(request, payload: dict, signature: str | None, timestamp: str | None):
    try:
        signature_valid = verify_webhook_signature(request.body, signature, timestamp)
    except ValidationError as exc:
        return Response({"detail": _error_message(exc)}, status=400)

    if not signature_valid:
        return Response({"detail": "Invalid Quidax webhook signature"}, status=401)

    try:
        return process_webhook(payload, signature=signature or "")
    except ValidationError as exc:
        return Response({"detail": _error_message(exc)}, status=400)


def webhook_test(request, payload: dict):
    if not request.auth.is_staff:
        return Response({"detail": "Admin access required"}, status=403)
    try:
        return process_webhook(payload, signature="swagger-test")
    except ValidationError as exc:
        return Response({"detail": _error_message(exc)}, status=400)


def diagnostics(request):
    if not request.auth.is_staff:
        return Response({"detail": "Admin access required"}, status=403)
    return get_quidax_diagnostics()


def sub_account(request):
    try:
        account = ensure_sub_account(request.auth)
    except ValidationError as exc:
        return Response({"detail": _error_message(exc)}, status=400)
    return {"quidax_id": account.quidax_id, "email": account.email}


def wallet_address(request, payload):
    try:
        address = ensure_wallet_address(
            request.auth,
            currency=payload.currency,
            network=payload.network or "",
        )
    except ValidationError as exc:
        return Response({"detail": _error_message(exc)}, status=400)
    return address


def wallet_balance(request, currency: str):
    try:
        balance = get_wallet_balance(request.auth, currency)
    except ValidationError as exc:
        return Response({"detail": _error_message(exc)}, status=400)
    return balance
