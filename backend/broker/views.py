
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
    is_deferred = transaction_id.startswith("quote_")
    
    if is_deferred:
        from django.db import transaction as db_transaction
        from broker.services import get_valid_quote
        from rates.models import RateQuote
        from quidax.models import QuidaxWalletAddress
        from quidax.services import create_pending_sell_deposit
        from django.utils import timezone
        from datetime import timedelta
        
        with db_transaction.atomic():
            quote_id = int(transaction_id.split("_")[1])
            quote = get_valid_quote(quote_id, RateQuote.SELL)
            
            transaction = Transaction.objects.create(
                user=request.auth,
                quote=quote,
                transaction_type=Transaction.SELL,
                asset=quote.asset,
                status=Transaction.PENDING_PAYMENT,
                naira_amount=quote.naira_amount,
                crypto_amount=quote.crypto_amount,
                market_rate=quote.market_rate,
                markup_percent=quote.markup_percent,
                final_rate=quote.final_rate,
                crypto_usd_price=quote.crypto_usd_price,
                network=quote.asset.network,
                broker_wallet_address="",
                crypto_source=Transaction.CRYPTO_SOURCE_EXTERNAL,
                payout_method=Transaction.PAYOUT_NGN_WALLET,
                expires_at=timezone.now() + timedelta(hours=24),
            )
            
            quidax_addr = QuidaxWalletAddress.objects.filter(
                user=request.auth, currency=quote.asset.code.upper()
            ).order_by('-created_at').first()
            
            if quidax_addr:
                transaction.broker_wallet_address = quidax_addr.address
                transaction.network = quidax_addr.network
                transaction.save(update_fields=["broker_wallet_address", "network"])
                create_pending_sell_deposit(
                    transaction_obj=transaction,
                    wallet_address=quidax_addr
                )
            
            return transition_transaction(transaction, Transaction.PENDING_REVIEW)
            
    else:
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
