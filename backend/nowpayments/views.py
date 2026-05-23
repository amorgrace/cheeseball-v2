from django.core.exceptions import ValidationError
from ninja.responses import Response

from .services import (
    create_custody_deposit,
    ensure_custody_account,
    get_custody_balance,
    get_nowpayments_diagnostics,
    process_custody_ipn,
    verify_ipn_signature,
)


def nowpayments_ipn(request, payload, signature: str | None):
    try:
        signature_valid = verify_ipn_signature(payload.dict(exclude_none=True), signature)
    except ValidationError as exc:
        return Response({"detail": str(exc)}, status=400)

    if not signature_valid:
        return Response({"detail": "Invalid NOWPayments IPN signature"}, status=401)

    try:
        return process_custody_ipn(payload.dict(exclude_none=True))
    except ValidationError as exc:
        return Response({"detail": str(exc)}, status=400)


def diagnostics(request):
    if not request.auth.is_staff:
        return Response({"detail": "Admin access required"}, status=403)
    return get_nowpayments_diagnostics()


def custody_account(request):
    try:
        account = ensure_custody_account(request.auth)
    except ValidationError as exc:
        return Response({"detail": str(exc)}, status=400)
    return {
        "sub_partner_id": account.sub_partner_id,
        "name": account.name,
    }


def custody_balance(request):
    try:
        account = ensure_custody_account(request.auth)
        balance = get_custody_balance(request.auth)
    except ValidationError as exc:
        return Response({"detail": str(exc)}, status=400)
    return {
        "account": {
            "sub_partner_id": account.sub_partner_id,
            "name": account.name,
        },
        "provider_balance": balance,
    }


def custody_deposit(request, payload):
    try:
        deposit = create_custody_deposit(
            request.auth,
            currency=payload.currency,
            amount=payload.amount,
        )
    except ValidationError as exc:
        return Response({"detail": str(exc)}, status=400)
    return {
        "id": str(deposit.id),
        "sub_partner_id": deposit.custody_account.sub_partner_id,
        "currency": deposit.currency,
        "amount": str(deposit.amount),
        "provider_payment_id": deposit.provider_payment_id,
        "pay_address": deposit.pay_address,
        "pay_amount": str(deposit.pay_amount) if deposit.pay_amount is not None else None,
        "payment_status": deposit.payment_status,
        "provider_payload": deposit.provider_payload,
    }
