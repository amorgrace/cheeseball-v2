import logging
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction as db_transaction
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


    if status in (Transaction.REJECTED, getattr(Transaction, 'CANCELLED', None)):
        if transaction.transaction_type == Transaction.SELL:
            _release_locked_crypto(transaction)

    if status == Transaction.COMPLETED:
        _pay_referral_reward(transaction.user)

        try:
            _finalize_transaction(transaction, admin_user=admin_user)
        except Exception:

            raise

    return transaction


REFERRAL_REWARD_NGN = Decimal("1000.00")
logger = logging.getLogger(__name__)


def _pay_referral_reward(user):
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
    with db_transaction.atomic():
        quote = get_valid_quote(payload.quote_id, RateQuote.BUY)
        transaction_obj = Transaction.objects.create(
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

        if payload.payment_method == Transaction.NGN_WALLET:
            _debit_ngn_wallet_for_buy(transaction_obj)
            transition_transaction(transaction_obj, Transaction.PAID)

        return transaction_obj


def _debit_ngn_wallet_for_buy(transaction_obj: Transaction) -> None:
    from rates.services import get_asset
    from wallets.models import Ledger
    from wallets.services import get_user_wallet

    ngn_asset = get_asset("NGN")
    wallet = get_user_wallet(transaction_obj.user, ngn_asset)

    if wallet.available_balance < transaction_obj.naira_amount:
        raise ValidationError("Insufficient balance in NGN wallet")

    balance_before = wallet.balance
    locked_before = wallet.locked_balance
    wallet.balance -= transaction_obj.naira_amount
    wallet.save(update_fields=["balance", "updated_at"])

    Ledger.objects.create(
        user=transaction_obj.user,
        wallet_balance=wallet,
        transaction_type=Ledger.BUY_PAYMENT,
        amount=transaction_obj.naira_amount,
        balance_before=balance_before,
        balance_after=wallet.balance,
        locked_before=locked_before,
        locked_after=wallet.locked_balance,
        reference_id=transaction_obj.id,
        reference_model="Transaction",
        notes=f"Buy {transaction_obj.id}",
    )


def build_sell_transaction(*, user, payload):
    quote = get_valid_quote(payload.quote_id, RateQuote.SELL)
    beneficiary = BeneficiaryBankAccount.objects.filter(id=payload.beneficiary_id, user=user).first()
    if not beneficiary:
        raise ValidationError("Beneficiary bank account not found")
    broker_wallet_address = get_broker_wallet_address(quote.asset)
    if not broker_wallet_address:
        raise ValidationError(f"Broker wallet address is not configured for {quote.asset.code}")

    from wallets.services import get_user_wallet, record_ledger
    from wallets.models import Ledger as WalletLedger

    user_wallet = get_user_wallet(user, quote.asset)
    if user_wallet.available_balance < quote.crypto_amount:
        raise ValidationError(f"Insufficient balance in {quote.asset.code}")

    user_wallet.locked_balance += quote.crypto_amount
    user_wallet.save(update_fields=["locked_balance", "updated_at"])


    record_ledger(user, user_wallet, WalletLedger.CONVERSION_LOCK, quote.crypto_amount, reference_model="Transaction")

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


def _release_locked_crypto(transaction_obj: Transaction):
    from django.db import transaction as db_transaction

    from wallets.services import get_user_wallet, record_ledger
    from wallets.models import Ledger as WalletLedger

    if transaction_obj.finalized:
        raise ValueError(f"Transaction {transaction_obj.id} already finalized")

    with db_transaction.atomic():
        asset = transaction_obj.asset
        user_wallet = get_user_wallet(transaction_obj.user, asset)

        if user_wallet.locked_balance < transaction_obj.crypto_amount:
            raise ValidationError("Locked balance insufficient for release")

        before_locked = user_wallet.locked_balance
        before_balance = user_wallet.balance

        user_wallet.locked_balance -= transaction_obj.crypto_amount
        user_wallet.save(update_fields=["locked_balance", "updated_at"])


        record_ledger(
            transaction_obj.user,
            user_wallet,
            WalletLedger.SELL_LOCK_RELEASED,
            transaction_obj.crypto_amount,
            reference_model="Transaction",
        )


def _finalize_transaction(transaction_obj: Transaction, admin_user=None):
    from django.db import transaction as db_transaction
    from rates.services import get_asset

    from wallets.services import deposit_to_wallet, get_user_wallet, record_ledger
    from wallets.models import PlatformReserve, ReserveMovement, Ledger as WalletLedger

    asset = transaction_obj.asset


    if transaction_obj.finalized:
        raise ValueError(f"Transaction {transaction_obj.id} already finalized")

    with db_transaction.atomic():

        if transaction_obj.transaction_type == Transaction.BUY:

            try:
                platform_reserve = PlatformReserve.objects.get(asset=asset)
            except PlatformReserve.DoesNotExist:
                raise ValidationError(f"Platform reserve not configured for {asset.code}")

            if platform_reserve.balance < transaction_obj.crypto_amount:
                raise ValidationError(f"Insufficient platform reserve for {asset.code}")


            deposit_to_wallet(transaction_obj.user, asset, transaction_obj.crypto_amount, notes=f"Buy {transaction_obj.id}")


            platform_reserve.balance -= transaction_obj.crypto_amount
            platform_reserve.save(update_fields=["balance"])
            ReserveMovement.objects.create(asset=asset, movement_type=ReserveMovement.OUT, amount=transaction_obj.crypto_amount, notes=f"Buy {transaction_obj.id}")


        elif transaction_obj.transaction_type == Transaction.SELL:

            try:
                platform_reserve = PlatformReserve.objects.get(asset=asset)
            except PlatformReserve.DoesNotExist:
                raise ValidationError(f"Platform reserve not configured for {asset.code}")


            user_wallet = get_user_wallet(transaction_obj.user, asset)
            if user_wallet.locked_balance < transaction_obj.crypto_amount:
                raise ValidationError("Locked balance insufficient at finalization")

            user_wallet.locked_balance -= transaction_obj.crypto_amount
            user_wallet.balance -= transaction_obj.crypto_amount
            user_wallet.save(update_fields=["balance", "locked_balance", "updated_at"])


            record_ledger(transaction_obj.user, user_wallet, WalletLedger.CONVERSION_DEBIT, transaction_obj.crypto_amount, reference_model="Transaction")


            ngn_asset = get_asset("NGN")
            deposit_to_wallet(transaction_obj.user, ngn_asset, transaction_obj.naira_amount, notes=f"Sell {transaction_obj.id}")


            platform_reserve.balance += transaction_obj.crypto_amount
            platform_reserve.save(update_fields=["balance"])
            ReserveMovement.objects.create(asset=asset, movement_type=ReserveMovement.IN, amount=transaction_obj.crypto_amount, notes=f"Sell {transaction_obj.id}")

        else:
            raise ValidationError("Unknown transaction type for finalization")


        transaction_obj.finalized = True
        transaction_obj.save(update_fields=["finalized"])
