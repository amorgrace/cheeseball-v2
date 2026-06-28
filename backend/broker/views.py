
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from ninja.responses import Response

from .models import Transaction
from .services import build_buy_transaction, build_sell_transaction, ensure_admin, transition_transaction, user_can_access, expire_stale_transactions


def create_buy_transaction(request, payload):
    try:
        return build_buy_transaction(user=request.auth, payload=payload)
    except ValidationError as e:
        return Response({"detail": str(e)}, status=400)


def create_sell_transaction(request, payload):
    try:
        return build_sell_transaction(user=request.auth, payload=payload)
    except ValidationError as e:
        return Response({"detail": str(e)}, status=400)


def list_transactions(request):
    # On-read expiry: fire the expiry check inline so stale pending_payment
    # transactions are automatically marked failed without needing a cron job.
    expire_stale_transactions()

    queryset = Transaction.objects.all() if request.auth.is_staff else Transaction.objects.filter(user=request.auth)
    return queryset.order_by("-created_at")


def get_transaction(request, transaction_id: str):
    transaction = get_object_or_404(Transaction, id=transaction_id)
    if not user_can_access(transaction, request.auth):
        return Response({"detail": "Transaction not found"}, status=404)
    return transaction


def confirm_sell_crypto_sent(request, transaction_id: str):
    transaction = get_object_or_404(Transaction, id=transaction_id, transaction_type=Transaction.SELL)
    if transaction.user_id != request.auth.id:
        return Response({"detail": "Transaction not found"}, status=404)
    if transaction.status != Transaction.PENDING_PAYMENT:
        return Response({"detail": "Transaction cannot be updated in its current state"}, status=400)
    return transition_transaction(transaction, Transaction.PENDING_REVIEW)


def approve_transaction(request, transaction_id: str, payload):
    ensure_admin(request.auth)
    transaction = get_object_or_404(Transaction, id=transaction_id)
    try:
        return transition_transaction(transaction, Transaction.PROCESSING, admin_user=request.auth, note=payload.note or "")
    except ValidationError as e:
        return Response({"detail": str(e)}, status=400)


def reject_transaction(request, transaction_id: str, payload):
    ensure_admin(request.auth)
    transaction = get_object_or_404(Transaction, id=transaction_id)
    try:
        return transition_transaction(transaction, Transaction.REJECTED, admin_user=request.auth, reason=payload.reason)
    except ValidationError as e:
        return Response({"detail": str(e)}, status=400)


def complete_transaction(request, transaction_id: str, payload):
    ensure_admin(request.auth)
    transaction = get_object_or_404(Transaction, id=transaction_id)
    try:
        return transition_transaction(transaction, Transaction.COMPLETED, admin_user=request.auth, note=payload.note or "")
    except ValidationError as e:
        return Response({"detail": str(e)}, status=400)


def fail_transaction(request, transaction_id: str, payload):
    ensure_admin(request.auth)
    transaction = get_object_or_404(Transaction, id=transaction_id)
    try:
        return transition_transaction(transaction, Transaction.FAILED, admin_user=request.auth, note=payload.note or "")
    except ValidationError as e:
        return Response({"detail": str(e)}, status=400)


def expire_stale_transactions_view(request):
    """Cron endpoint to expire stale pending transactions."""
    count = expire_stale_transactions()
    return {"detail": f"Successfully expired {count} stale transactions."}
