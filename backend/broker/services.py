from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from rates.models import Asset, RateQuote

from .models import Transaction


def ensure_admin(user):
    if not user.is_staff:
        raise PermissionDenied("Admin access required")


def get_valid_quote(quote_id: int, quote_type: str) -> RateQuote:
    quote = RateQuote.objects.filter(id=quote_id, quote_type=quote_type).first()
    if not quote:
        raise ValidationError("Quote not found")
    if quote.is_expired:
        raise ValidationError("Quote has expired")
    return quote


def get_broker_wallet_address(asset: Asset) -> str:
    return asset.broker_wallet_address or getattr(settings, f"BROKER_{asset.code}_WALLET_ADDRESS", "")


def transition_transaction(transaction: Transaction, status: str, *, admin_user=None, note: str = "", reason: str = "") -> Transaction:
    now = timezone.now()
    transaction.status = status
    if note:
        transaction.admin_notes = note
    if reason:
        transaction.rejection_reason = reason

    update_fields = ["status", "admin_notes", "rejection_reason"]

    if admin_user:
        transaction.approved_by = admin_user
        update_fields.append("approved_by")

    if status in {Transaction.PAID, Transaction.PENDING_REVIEW}:
        transaction.paid_at = now
        update_fields.append("paid_at")
    if status in {Transaction.PROCESSING, Transaction.REJECTED, Transaction.FAILED}:
        transaction.reviewed_at = now
        update_fields.append("reviewed_at")
    if status == Transaction.COMPLETED:
        transaction.completed_at = now
        update_fields.append("completed_at")
    if status == Transaction.FAILED:
        transaction.failed_at = now
        update_fields.append("failed_at")

    transaction.save(update_fields=update_fields)
    return transaction


def build_buy_transaction(*, user, payload):
    quote = get_valid_quote(payload.quote_id, RateQuote.BUY)
    return Transaction.objects.create(
        user=user,
        quote=quote,
        transaction_type=Transaction.BUY,
        asset=quote.asset,
        status=Transaction.PENDING_PAYMENT,
        payment_method=payload.payment_method,
        naira_amount=quote.naira_amount,
        crypto_amount=quote.crypto_amount,
        market_rate=quote.market_rate,
        markup_percent=quote.markup_percent,
        final_rate=quote.final_rate,
        wallet_address=payload.wallet_address.strip(),
        network=(payload.network or "").strip(),
    )


def build_sell_transaction(*, user, payload):
    quote = get_valid_quote(payload.quote_id, RateQuote.SELL)
    return Transaction.objects.create(
        user=user,
        quote=quote,
        transaction_type=Transaction.SELL,
        asset=quote.asset,
        status=Transaction.PENDING_PAYMENT,
        naira_amount=quote.naira_amount,
        crypto_amount=quote.crypto_amount,
        market_rate=quote.market_rate,
        markup_percent=quote.markup_percent,
        final_rate=quote.final_rate,
        broker_wallet_address=get_broker_wallet_address(quote.asset),
        bank_name=payload.bank_name.strip(),
        bank_account_name=payload.bank_account_name.strip(),
        bank_account_number=payload.bank_account_number.strip(),
    )


def user_can_access(transaction: Transaction, user) -> bool:
    return transaction.user_id == user.id or user.is_staff
