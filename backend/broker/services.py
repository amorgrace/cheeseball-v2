import logging
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction as db_transaction
from django.utils import timezone

from rates.models import Asset, RateQuote
from payouts.models import BeneficiaryBankAccount

from .models import Transaction

AUTOMATED_BUY_ASSET_CODES = {"BTC", "ETH", "USDT"}
AUTOMATED_BUY_PAYMENT_METHODS = {Transaction.PAYSTACK, Transaction.NGN_WALLET}
MANUAL_BUY_PAYMENT_METHODS = {Transaction.BANK_TRANSFER}


def ensure_admin(user):
    if not user.is_staff:
        raise PermissionDenied("Admin access required")


def validate_transaction_transition(transaction: Transaction, target_status: str) -> None:
    allowed_transitions = {
        Transaction.PENDING_PAYMENT: {Transaction.PENDING_REVIEW, Transaction.PAID, Transaction.FAILED},
        Transaction.PENDING_REVIEW: {Transaction.PAID, Transaction.PROCESSING, Transaction.REJECTED, Transaction.FAILED},
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


def validate_buy_payment_method(asset: Asset, payment_method: str) -> None:
    if asset.code in AUTOMATED_BUY_ASSET_CODES:
        if payment_method not in AUTOMATED_BUY_PAYMENT_METHODS:
            raise ValidationError(
                f"{asset.code} purchases support Paystack bank transfer or NGN wallet only."
            )
        return

    if payment_method not in MANUAL_BUY_PAYMENT_METHODS:
        raise ValidationError(f"{asset.code} purchases require manual bank transfer.")


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
        if transaction.transaction_type == Transaction.SELL and transaction.crypto_source == Transaction.CRYPTO_SOURCE_CHEESEBALL:
            _release_locked_crypto(transaction)

    if status == Transaction.COMPLETED:
        _pay_referral_reward(transaction.user)

        try:
            _finalize_transaction(transaction, admin_user=admin_user)
        except Exception:

            raise

    # --- Send in-app notification ---
    _notify_transaction_status(transaction, status)

    return transaction


REFERRAL_REWARD_NGN = Decimal("1000.00")
logger = logging.getLogger(__name__)


def _notify_transaction_status(transaction: Transaction, status: str):
    """Send an in-app notification when a transaction reaches a terminal status."""
    from notifications.models import Notification
    from notifications.services import notify

    txn_type = transaction.transaction_type.capitalize()
    asset_code = transaction.asset.code
    amount = transaction.crypto_amount

    if status == Transaction.COMPLETED:
        notify(
            transaction.user,
            title=f"{txn_type} Order Completed",
            message=f"Your {txn_type.lower()} order for {amount} {asset_code} has been completed successfully.",
            notification_type=Notification.TRANSACTION_COMPLETED,
            reference_id=transaction.id,
            reference_type="Transaction",
        )
    elif status == Transaction.FAILED:
        notify(
            transaction.user,
            title=f"{txn_type} Order Failed",
            message=f"Your {txn_type.lower()} order for {amount} {asset_code} has failed. Please contact support.",
            notification_type=Notification.TRANSACTION_FAILED,
            reference_id=transaction.id,
            reference_type="Transaction",
        )
    elif status == Transaction.REJECTED:
        reason = transaction.rejection_reason or "No reason provided."
        notify(
            transaction.user,
            title=f"{txn_type} Order Rejected",
            message=f"Your {txn_type.lower()} order for {amount} {asset_code} was rejected. Reason: {reason}",
            notification_type=Notification.TRANSACTION_REJECTED,
            reference_id=transaction.id,
            reference_type="Transaction",
        )


def _pay_referral_reward(user):
    if user.referral_reward_paid or not user.referred_by_id:
        return

    from notifications.models import Notification
    from notifications.services import notify
    from rates.services import get_asset
    from wallets.services import deposit_to_wallet

    try:
        ngn = get_asset("NGN")
        deposit_to_wallet(user.referred_by, ngn, REFERRAL_REWARD_NGN, notes=f"Referral reward for {user.email}")
        user.referral_reward_paid = True
        user.save(update_fields=["referral_reward_paid"])

        # Notify the referrer
        notify(
            user.referred_by,
            title="Referral Reward Received!",
            message=f"You earned ₦{REFERRAL_REWARD_NGN:,.0f} because {user.email} completed their first trade.",
            notification_type=Notification.REFERRAL_REWARD,
        )
    except Exception:
        logger.exception("Failed to pay referral reward for %s", user.email)


def build_buy_transaction(*, user, payload):
    with db_transaction.atomic():
        quote = get_valid_quote(payload.quote_id, RateQuote.BUY)
        validate_buy_payment_method(quote.asset, payload.payment_method)
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
            crypto_usd_price=quote.crypto_usd_price,
            wallet_address=(payload.wallet_address or "").strip(),
            network=(payload.network or "").strip(),
        )

        if payload.payment_method == Transaction.NGN_WALLET:
            _debit_ngn_wallet_for_buy(transaction_obj)
            transition_transaction(transaction_obj, Transaction.PAID)
            try_auto_complete_buy(transaction_obj)

        return transaction_obj


def try_auto_complete_buy(transaction_obj: Transaction):
    from wallets.models import PlatformReserve
    
    if transaction_obj.transaction_type != Transaction.BUY:
        return
    
    if transaction_obj.status != Transaction.PAID:
        return

    try:
        platform_reserve = PlatformReserve.objects.get(asset=transaction_obj.asset)
        if platform_reserve.balance >= transaction_obj.crypto_amount:
            transition_transaction(transaction_obj, Transaction.PROCESSING, note="Auto-processing verified payment")
            transition_transaction(transaction_obj, Transaction.COMPLETED, note="Auto-completed verified payment")
        else:
            logger.warning("Insufficient PlatformReserve to auto-complete buy transaction %s", transaction_obj.id)
    except PlatformReserve.DoesNotExist:
        logger.warning("PlatformReserve not found to auto-complete buy transaction %s", transaction_obj.id)


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
    with db_transaction.atomic():
        quote = get_valid_quote(payload.quote_id, RateQuote.SELL)
        payout_method = getattr(payload, "payout_method", Transaction.PAYOUT_BANK)
        crypto_source = getattr(payload, "crypto_source", Transaction.CRYPTO_SOURCE_EXTERNAL)
        beneficiary = None

        if payout_method not in {Transaction.PAYOUT_BANK, Transaction.PAYOUT_NGN_WALLET}:
            raise ValidationError("payout_method must be beneficiary_bank or ngn_wallet")

        if payout_method == Transaction.PAYOUT_BANK:
            beneficiary = BeneficiaryBankAccount.objects.filter(id=payload.beneficiary_id, user=user).first()
            if not beneficiary:
                raise ValidationError("Beneficiary bank account not found")

        selected_network = (getattr(payload, "network", None) or "").strip() or quote.asset.network

        # --- External wallet: generate Quidax deposit address ---
        custody_deposit = None
        broker_wallet_address = ""
        quidax_wallet_address_obj = None

        if crypto_source == Transaction.CRYPTO_SOURCE_EXTERNAL:
            try:
                from quidax.services import ensure_wallet_address
                quidax_wallet_address_obj = ensure_wallet_address(
                    user,
                    currency=quote.asset.code,
                    network=selected_network,
                )
                broker_wallet_address = quidax_wallet_address_obj.address
            except Exception:
                logger.exception("Failed to create Quidax deposit wallet for sell — falling back to static address")
                broker_wallet_address = (getattr(payload, "broker_wallet_address", None) or "").strip() or get_broker_wallet_address(quote.asset)

            if not broker_wallet_address and not quidax_wallet_address_obj:
                raise ValidationError(f"Broker wallet address is not configured for {quote.asset.code}")
        else:
            # Internal wallet: validate balance
            from wallets.services import get_user_wallet
            wallet = get_user_wallet(user, quote.asset)
            if wallet.available_balance < quote.crypto_amount:
                raise ValidationError(f"Insufficient {quote.asset.code} balance in your wallet")

        transaction_obj = Transaction.objects.create(
            user=user,
            quote=quote,
            custody_deposit=custody_deposit,
            transaction_type=Transaction.SELL,
            asset=quote.asset,
            status=Transaction.PENDING_PAYMENT,
            naira_amount=quote.naira_amount,
            crypto_amount=quote.crypto_amount,
            market_rate=quote.market_rate,
            markup_percent=quote.markup_percent,
            final_rate=quote.final_rate,
            crypto_usd_price=quote.crypto_usd_price,
            network=selected_network,
            broker_wallet_address=broker_wallet_address,
            crypto_source=crypto_source,
            payout_method=payout_method,
            bank_name=beneficiary.bank_name if beneficiary else "",
            bank_account_name=beneficiary.account_name if beneficiary else "",
            bank_account_number=beneficiary.account_number if beneficiary else "",
            bank_account_type=beneficiary.account_type if beneficiary else "",
        )

        if crypto_source == Transaction.CRYPTO_SOURCE_EXTERNAL and quidax_wallet_address_obj:
            from quidax.services import create_pending_sell_deposit
            create_pending_sell_deposit(
                transaction_obj=transaction_obj,
                wallet_address=quidax_wallet_address_obj
            )

        # --- Internal wallet: lock crypto and auto-advance ---
        if crypto_source == Transaction.CRYPTO_SOURCE_CHEESEBALL:
            _lock_crypto_for_sell(transaction_obj)
            transition_transaction(transaction_obj, Transaction.PAID)
            transition_transaction(transaction_obj, Transaction.PROCESSING, note="Auto-processing internal wallet sell")
            transition_transaction(transaction_obj, Transaction.COMPLETED, note="Auto-completed internal wallet sell")

        return transaction_obj


def _lock_crypto_for_sell(transaction_obj: Transaction) -> None:
    """Lock user's crypto balance for an internal wallet sell."""
    from wallets.models import Ledger as WalletLedger
    from wallets.services import get_user_wallet, record_ledger

    wallet = get_user_wallet(transaction_obj.user, transaction_obj.asset)
    if wallet.available_balance < transaction_obj.crypto_amount:
        raise ValidationError(f"Insufficient {transaction_obj.asset.code} balance")

    wallet.locked_balance += transaction_obj.crypto_amount
    wallet.save(update_fields=["locked_balance", "updated_at"])

    record_ledger(
        transaction_obj.user,
        wallet,
        WalletLedger.SELL_LOCK_RELEASED,  # reuse existing ledger type for sell lock
        transaction_obj.crypto_amount,
        reference_id=transaction_obj.id,
        reference_model="Transaction",
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


            if transaction_obj.wallet_address:
                from quidax.services import initiate_crypto_withdrawal
                try:
                    quidax_response = initiate_crypto_withdrawal(
                        transaction_obj.user,
                        currency=asset.code,
                        amount=transaction_obj.crypto_amount,
                        fund_uid=transaction_obj.wallet_address,
                        network=transaction_obj.network
                    )
                    current_notes = transaction_obj.admin_notes or ""
                    transaction_obj.admin_notes = f"{current_notes}\nQuidax Tx: {quidax_response.get('id') or quidax_response}".strip()
                except Exception as e:
                    logger.exception("Automated Quidax payout failed")
                    raise ValidationError(f"External payout failed: {str(e)}")
                    
                platform_reserve.balance -= transaction_obj.crypto_amount
                platform_reserve.save(update_fields=["balance"])
                ReserveMovement.objects.create(asset=asset, movement_type=ReserveMovement.OUT, amount=transaction_obj.crypto_amount, notes=f"Buy & Direct Payout {transaction_obj.id}")
            else:
                deposit_to_wallet(transaction_obj.user, asset, transaction_obj.crypto_amount, notes=f"Buy {transaction_obj.id}")

                platform_reserve.balance -= transaction_obj.crypto_amount
                platform_reserve.save(update_fields=["balance"])
                ReserveMovement.objects.create(asset=asset, movement_type=ReserveMovement.OUT, amount=transaction_obj.crypto_amount, notes=f"Buy {transaction_obj.id}")


        elif transaction_obj.transaction_type == Transaction.SELL:

            try:
                platform_reserve = PlatformReserve.objects.get(asset=asset)
            except PlatformReserve.DoesNotExist:
                raise ValidationError(f"Platform reserve not configured for {asset.code}")


            if transaction_obj.crypto_source == Transaction.CRYPTO_SOURCE_CHEESEBALL:
                user_wallet = get_user_wallet(transaction_obj.user, asset)
                if user_wallet.locked_balance < transaction_obj.crypto_amount:
                    raise ValidationError("Locked balance insufficient at finalization")

                user_wallet.locked_balance -= transaction_obj.crypto_amount
                user_wallet.balance -= transaction_obj.crypto_amount
                user_wallet.save(update_fields=["balance", "locked_balance", "updated_at"])


                record_ledger(transaction_obj.user, user_wallet, WalletLedger.CONVERSION_DEBIT, transaction_obj.crypto_amount, reference_id=transaction_obj.id, reference_model="Transaction")


            if transaction_obj.payout_method == Transaction.PAYOUT_NGN_WALLET:
                ngn_asset = get_asset("NGN")
                deposit_to_wallet(transaction_obj.user, ngn_asset, transaction_obj.naira_amount, notes=f"Sell {transaction_obj.id}")
            elif transaction_obj.payout_method == Transaction.PAYOUT_BANK:
                try:
                    from payments.transfers import process_sell_payout
                    process_sell_payout(transaction_obj)
                except Exception:
                    logger.exception("Paystack payout failed for transaction %s — requires manual payout", transaction_obj.id)

            platform_reserve.balance += transaction_obj.crypto_amount
            platform_reserve.save(update_fields=["balance"])
            ReserveMovement.objects.create(asset=asset, movement_type=ReserveMovement.IN, amount=transaction_obj.crypto_amount, notes=f"Sell {transaction_obj.id}")

        else:
            raise ValidationError("Unknown transaction type for finalization")

        transaction_obj.finalized = True
        transaction_obj.save(update_fields=["finalized"])


def expire_stale_transactions():
    """Fail transactions that have been stuck in PENDING_PAYMENT for over 24 hours."""
    from datetime import timedelta
    cutoff = timezone.now() - timedelta(hours=24)
    
    stale_txns = Transaction.objects.filter(
        status=Transaction.PENDING_PAYMENT,
        created_at__lte=cutoff
    )
    
    count = 0
    for txn in stale_txns:
        try:
            transition_transaction(txn, Transaction.FAILED, reason="Expired after 24 hours of inactivity")
            count += 1
        except Exception:
            logger.exception("Failed to auto-expire transaction %s", txn.id)
            
    return count
