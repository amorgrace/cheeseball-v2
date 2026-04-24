import logging
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from rates.models import Asset, RateQuote
from payouts.models import BeneficiaryBankAccount

from .models import Transaction


def ensure_admin(user):
    if not user.is_staff:
        raise PermissionDenied("Admin access required")


def validate_transaction_transition(transaction: Transaction, target_status: str) -> None:
    allowed_transitions = {
        Transaction.PENDING_PAYMENT: {Transaction.PENDING_REVIEW, Transaction.FAILED},
        Transaction.PENDING_REVIEW: {Transaction.PAID, Transaction.REJECTED, Transaction.FAILED},
        Transaction.PAID: {Transaction.PROCESSING, Transaction.COMPLETED, Transaction.FAILED},
        Transaction.PROCESSING: {Transaction.COMPLETED, Transaction.FAILED},
        Transaction.COMPLETED: set(),
        Transaction.FAILED: set(),
        Transaction.REJECTED: set(),
    }
    current_status = transaction.status
    if target_status == current_status:
        return
    if target_status not in allowed_transitions.get(current_status, set()):
        raise ValidationError(f"Cannot change transaction status from {current_status} to {target_status}")


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
    validate_transaction_transition(transaction, status)
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

    if status == Transaction.COMPLETED:
        _pay_referral_reward(transaction.user)

    return transaction


REFERRAL_REWARD_NGN = Decimal("1000.00")
logger = logging.getLogger(__name__)


def _pay_referral_reward(user):
    """Credit the referrer ₦1,000 on the referred user's first completed transaction."""
    if user.referral_reward_paid or not user.referred_by_id:
        return

    from rates.services import get_asset
    from wallets.services import deposit_to_wallet

    try:
        ngn = get_asset("NGN")
        deposit_to_wallet(user.referred_by, ngn, REFERRAL_REWARD_NGN, notes=f"Referral reward for {user.email}")
        user.referral_reward_paid = True
        user.save(update_fields=["referral_reward_paid"])
    except Exception:
        logger.exception("Failed to pay referral reward for %s", user.email)


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
    beneficiary = BeneficiaryBankAccount.objects.filter(id=payload.beneficiary_id, user=user).first()
    if not beneficiary:
        raise ValidationError("Beneficiary bank account not found")
    broker_wallet_address = get_broker_wallet_address(quote.asset)
    if not broker_wallet_address:
        raise ValidationError(f"Broker wallet address is not configured for {quote.asset.code}")
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
        broker_wallet_address=broker_wallet_address,
        bank_name=beneficiary.bank_name,
        bank_account_name=beneficiary.account_name,
        bank_account_number=beneficiary.account_number,
        bank_account_type=beneficiary.account_type,
    )


def user_can_access(transaction: Transaction, user) -> bool:
    return transaction.user_id == user.id or user.is_staff
