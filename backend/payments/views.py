import hashlib
import hmac
import uuid

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja.responses import Response

from broker.models import Transaction
from broker.services import ensure_admin, transition_transaction

from .models import PaymentRecord


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
            "provider": "paystack" if payload.payment_method == PaymentRecord.PAYSTACK else "manual",
        },
    )
    if payment_record.method != payload.payment_method:
        payment_record.method = payload.payment_method
        payment_record.provider = "paystack" if payload.payment_method == PaymentRecord.PAYSTACK else "manual"
        payment_record.save(update_fields=["method", "provider"])

    if payload.payment_method == PaymentRecord.PAYSTACK:
        payment_record.provider_reference = f"cb_{uuid.uuid4().hex[:20]}"
        payment_record.save(update_fields=["provider_reference"])

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
    payment_record = PaymentRecord.objects.filter(provider_reference=reference, method=PaymentRecord.PAYSTACK).first()
    if not payment_record:
        return {"message": "Webhook ignored"}

    payment_record.provider_payload = data
    payment_record.user_confirmed_at = timezone.now()

    if event_name == "charge.success" and status == "success":
        payment_record.status = PaymentRecord.VERIFIED
        payment_record.verified_at = timezone.now()
        payment_record.save(update_fields=["provider_payload", "user_confirmed_at", "status", "verified_at"])
        transition_transaction(payment_record.transaction, Transaction.PAID)
    else:
        payment_record.status = PaymentRecord.FAILED
        payment_record.save(update_fields=["provider_payload", "user_confirmed_at", "status"])

    return {"message": "Webhook processed"}
