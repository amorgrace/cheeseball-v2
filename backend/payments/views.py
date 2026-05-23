import hashlib
import hmac
import json
import uuid
from datetime import timedelta
from decimal import ROUND_HALF_UP
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja.responses import Response

from broker.models import Transaction
from broker.services import ensure_admin, transition_transaction

from .models import PaymentRecord


def _paystack_reference() -> str:
    return f"cb-{uuid.uuid4().hex[:20]}"


def _amount_to_kobo(amount) -> int:
    return int((amount * 100).quantize(0, rounding=ROUND_HALF_UP))


def _paystack_charge_payload(transaction, reference: str) -> dict:
    expires_at = timezone.now() + timedelta(minutes=settings.PAYSTACK_BANK_TRANSFER_EXPIRES_MINUTES)
    return {
        "email": transaction.user.email,
        "amount": str(_amount_to_kobo(transaction.naira_amount)),
        "currency": settings.PAYSTACK_CURRENCY,
        "reference": reference,
        "bank_transfer": {
            "account_expires_at": expires_at.isoformat(),
        },
        "metadata": {
            "transaction_id": str(transaction.id),
            "asset": transaction.asset_code,
            "crypto_amount": str(transaction.crypto_amount),
        },
    }


def _create_paystack_bank_transfer_charge(transaction, reference: str) -> dict:
    if not settings.PAYSTACK_SECRET_KEY:
        raise ValidationError("Paystack secret key is not configured")

    request = Request(
        settings.PAYSTACK_CHARGE_URL,
        data=json.dumps(_paystack_charge_payload(transaction, reference)).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "CheeseBall/1.0 (+https://cheeseballapp.com)",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise ValidationError(f"Paystack charge failed: {error_body}") from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ValidationError("Unable to create Paystack bank transfer charge") from exc

    if not result.get("status"):
        raise ValidationError(result.get("message") or "Paystack charge failed")
    return result


def get_payment_instructions():
    return {
        "bank_name": settings.BANK_NAME,
        "account_name": settings.BANK_ACCOUNT_NAME,
        "account_number": settings.BANK_ACCOUNT_NUMBER,
        "paystack_public_key": settings.PAYSTACK_PUBLIC_KEY,
    }


def setup_payment(request, payload):
    transaction = get_object_or_404(Transaction, id=payload.transaction_id)
    if transaction.user_id != request.auth.id and not request.auth.is_staff:
        return Response({"detail": "Transaction not found"}, status=404)
    if transaction.transaction_type != Transaction.BUY:
        return Response({"detail": "Payment setup is only available for buy transactions"}, status=400)
    if transaction.payment_method != payload.payment_method:
        return Response({"detail": "Payment method does not match this transaction"}, status=400)

    payment_record, _ = PaymentRecord.objects.get_or_create(
        transaction=transaction,
        defaults={
            "method": payload.payment_method,
            "provider": "paystack" if payload.payment_method == PaymentRecord.PAYSTACK else "wallet" if payload.payment_method == PaymentRecord.NGN_WALLET else "manual",
        },
    )
    if payment_record.method != payload.payment_method:
        payment_record.method = payload.payment_method
        payment_record.provider = "paystack" if payload.payment_method == PaymentRecord.PAYSTACK else "wallet" if payload.payment_method == PaymentRecord.NGN_WALLET else "manual"
        payment_record.save(update_fields=["method", "provider"])

    if payload.payment_method == PaymentRecord.PAYSTACK:
        if payment_record.status != PaymentRecord.VERIFIED:
            try:
                reference = payment_record.provider_reference or _paystack_reference()
                charge_response = _create_paystack_bank_transfer_charge(transaction, reference)
            except ValidationError as e:
                return Response({"detail": str(e)}, status=400)

            payment_record.status = PaymentRecord.PENDING
            payment_record.provider = "paystack"
            payment_record.provider_reference = reference
            payment_record.provider_payload = charge_response
            payment_record.save(update_fields=["status", "provider", "provider_reference", "provider_payload"])
    elif payload.payment_method == PaymentRecord.NGN_WALLET:
        payment_record.status = PaymentRecord.VERIFIED
        payment_record.provider_reference = f"wallet_{transaction.id}"
        payment_record.user_confirmed_at = transaction.paid_at or timezone.now()
        payment_record.verified_at = transaction.paid_at or timezone.now()
        payment_record.save(update_fields=["status", "provider_reference", "user_confirmed_at", "verified_at"])

    return payment_record


def submit_bank_transfer(request, transaction_id, payload):
    transaction = get_object_or_404(
        Transaction,
        id=transaction_id,
        transaction_type=Transaction.BUY,
        payment_method=Transaction.BANK_TRANSFER,
    )
    if transaction.user_id != request.auth.id:
        return Response({"detail": "Transaction not found"}, status=404)
    if transaction.status != Transaction.PENDING_PAYMENT:
        return Response({"detail": "Transfer proof can only be submitted for pending payment transactions"}, status=400)

    payment_record, _ = PaymentRecord.objects.get_or_create(
        transaction=transaction,
        defaults={"method": PaymentRecord.BANK_TRANSFER, "provider": "manual"},
    )
    payment_record.status = PaymentRecord.PENDING_REVIEW
    payment_record.receipt_reference = payload.receipt_reference.strip()
    payment_record.receipt_url = payload.receipt_url.strip()
    payment_record.receipt_note = (payload.receipt_note or "").strip()
    payment_record.user_confirmed_at = timezone.now()
    payment_record.save(
        update_fields=["status", "receipt_reference", "receipt_url", "receipt_note", "user_confirmed_at"]
    )
    transition_transaction(transaction, Transaction.PENDING_REVIEW)
    return payment_record


def verify_bank_transfer(request, transaction_id):
    ensure_admin(request.auth)
    transaction = get_object_or_404(
        Transaction,
        id=transaction_id,
        transaction_type=Transaction.BUY,
        payment_method=Transaction.BANK_TRANSFER,
    )
    if transaction.status != Transaction.PENDING_REVIEW:
        return Response({"detail": "Only transactions pending review can be verified"}, status=400)
    payment_record = get_object_or_404(PaymentRecord, transaction=transaction)
    if payment_record.status != PaymentRecord.PENDING_REVIEW:
        return Response({"detail": "Transfer proof must be pending review before verification"}, status=400)
    payment_record.status = PaymentRecord.VERIFIED
    payment_record.verified_at = timezone.now()
    payment_record.save(update_fields=["status", "verified_at"])
    transition_transaction(transaction, Transaction.PAID, admin_user=request.auth)
    return payment_record


def paystack_webhook(request, payload, signature: str | None):
    secret = settings.PAYSTACK_WEBHOOK_SECRET
    if secret:
        body = request.body or b""
        digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha512).hexdigest()
        if not signature or not hmac.compare_digest(digest, signature):
            return Response({"detail": "Invalid webhook signature"}, status=401)

    event_name = payload.event
    data = payload.data or {}
    reference = data.get("reference", "")
    status = data.get("status", "")
    amount = data.get("amount")
    requested_amount = data.get("requested_amount")
    currency = data.get("currency", "")
    channel = data.get("channel", "")
    payment_record = PaymentRecord.objects.filter(provider_reference=reference, method=PaymentRecord.PAYSTACK).first()
    if not payment_record:
        return {"message": "Webhook ignored"}

    transaction = payment_record.transaction
    payment_record.provider_payload = data
    payment_record.user_confirmed_at = timezone.now()

    if event_name == "charge.success" and status == "success":
        expected_amount = _amount_to_kobo(transaction.naira_amount)
        settled_amount = requested_amount if requested_amount is not None else amount
        if int(settled_amount or 0) != expected_amount or currency != settings.PAYSTACK_CURRENCY:
            payment_record.status = PaymentRecord.PENDING_REVIEW
            payment_record.save(update_fields=["provider_payload", "user_confirmed_at", "status"])
            if transaction.status == Transaction.PENDING_PAYMENT:
                transition_transaction(transaction, Transaction.PENDING_REVIEW)
            return {"message": "Webhook requires review"}
        if channel and channel != "bank_transfer":
            payment_record.status = PaymentRecord.PENDING_REVIEW
            payment_record.save(update_fields=["provider_payload", "user_confirmed_at", "status"])
            if transaction.status == Transaction.PENDING_PAYMENT:
                transition_transaction(transaction, Transaction.PENDING_REVIEW)
            return {"message": "Webhook requires review"}

        payment_record.status = PaymentRecord.VERIFIED
        payment_record.verified_at = timezone.now()
        payment_record.save(update_fields=["provider_payload", "user_confirmed_at", "status", "verified_at"])
        if transaction.status == Transaction.PENDING_PAYMENT:
            transition_transaction(transaction, Transaction.PAID)
    elif event_name in {"charge.failed", "bank.transfer.rejected"} or status == "failed":
        payment_record.status = PaymentRecord.FAILED
        payment_record.save(update_fields=["provider_payload", "user_confirmed_at", "status"])

    return {"message": "Webhook processed"}
