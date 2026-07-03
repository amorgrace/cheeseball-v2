import logging
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction as db_transaction
from django.db.models import Q
from django.utils import timezone

from rates.models import Asset, RateQuote
from payouts.models import BeneficiaryBankAccount

from .models import Transaction

# All assets support automated payment methods (Paystack / NGN wallet)
# for the buy flow because it is purely in-app ledger crediting — no
# on-chain send is required from us at buy time.
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
    """All assets accept Paystack or NGN-wallet for buy orders.

    Buying crypto is purely an internal ledger credit — we receive the NGN
    payment, confirm it, then credit the user's in-app wallet.  There is no
    on-chain transaction required from us at buy time, so there is no reason
    to restrict any asset to manual bank-transfer only.
    """
    if payment_method not in AUTOMATED_BUY_PAYMENT_METHODS | MANUAL_BUY_PAYMENT_METHODS:
        raise ValidationError(
            f"Invalid payment method '{payment_method}' for buying {asset.code}."
        )


def transition_transaction(transaction: Transaction, status: str, *, admin_user=None, note: str = "", reason: str = "", fail_reason: str = "") -> Transaction:
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
        if fail_reason:
            transaction.fail_reason = fail_reason
            update_fields.append("fail_reason")

    transaction.save(update_fields=update_fields)

    # Send Admin Telegram Notification for Pending Review
    if status == Transaction.PENDING_REVIEW:
        try:
            import html
            from notifications.telegram import send_telegram_alert
            txn_type_str = transaction.transaction_type.upper()
            asset_code_str = transaction.asset.code
            naira_amt = getattr(transaction, 'naira_amount', 0) or 0
            crypto_amt = getattr(transaction, 'crypto_amount', 0) or 0
            
            telegram_msg = (
                f"📥 <b>Transaction Awaiting Review</b>\n"
                f"<b>Type:</b> {html.escape(txn_type_str)}\n"
                f"<b>User:</b> {html.escape(transaction.user.email)}\n"
                f"<b>Asset:</b> {html.escape(asset_code_str)}\n"
                f"<b>Crypto Amount:</b> {crypto_amt}\n"
                f"<b>Naira Amount:</b> ₦{naira_amt:,.2f} NGN\n"
                f"<b>Payment Method:</b> {html.escape(transaction.payment_method or 'N/A')}\n"
                f"<b>Status:</b> Awaiting Review"
            )
            send_telegram_alert(telegram_msg)
        except Exception:
            pass

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
        if transaction.transaction_type == Transaction.SELL:
            import decimal
            from django.utils import timezone

            local_dt = timezone.localtime(transaction.completed_at or transaction.updated_at or timezone.now())
            formatted_date = local_dt.strftime("%m/%d/%Y, %I:%M %p")

            symbols_map = {
                "USDT": "₮",
                "BTC": "₿",
                "ETH": "Ξ",
                "SOL": "S",
                "USDC": "$",
            }
            asset_symbol = symbols_map.get(asset_code.upper(), asset_code[0] if asset_code else "")

            usd_value = None
            if transaction.crypto_usd_price:
                usd_amt = transaction.crypto_amount * transaction.crypto_usd_price
                usd_value = f"{usd_amt:,.2f}"

            extra_ctx = {
                "template_name": "emails/sell_transaction_confirmed.html",
                "text_template_name": "emails/sell_transaction_confirmed.txt",
                "crypto_amount": f"{transaction.crypto_amount:g}" if isinstance(transaction.crypto_amount, decimal.Decimal) else f"{transaction.crypto_amount}",
                "asset_code": asset_code,
                "naira_amount": f"{transaction.naira_amount:,.2f}",
                "formatted_date": formatted_date,
                "reference": transaction.id,
                "asset_symbol": asset_symbol,
                "usd_value": usd_value,
                "payout_method": "NGN Wallet",
                "cta_url": "https://cheeseballapp.com/dashboard/history",
                "secondary_cta_url": "https://cheeseballapp.com/dashboard/sell",
            }
            notify(
                transaction.user,
                title="Sell Crypto — Transaction Confirmed",
                message=f"You sold {transaction.crypto_amount} {asset_code} and received ₦{transaction.naira_amount:,.2f} — transaction completed successfully.",
                notification_type=Notification.TRANSACTION_COMPLETED,
                reference_id=transaction.id,
                reference_type="Transaction",
                extra_context=extra_ctx,
            )
        else:
            if transaction.transaction_type == Transaction.BUY:
                import decimal
                from django.utils import timezone
                local_dt = timezone.localtime(transaction.completed_at or transaction.updated_at or timezone.now())
                formatted_date = local_dt.strftime("%m/%d/%Y, %I:%M %p")
                symbols_map = {
                    "USDT": "₮",
                    "BTC": "₿",
                    "ETH": "Ξ",
                    "SOL": "S",
                    "USDC": "$",
                }
                asset_symbol = symbols_map.get(asset_code.upper(), asset_code[0] if asset_code else "")
                usd_value = None
                if transaction.crypto_usd_price:
                    usd_amt = transaction.crypto_amount * transaction.crypto_usd_price
                    usd_value = f"{usd_amt:,.2f}"

                pm_map = {
                    Transaction.PAYSTACK: "Paystack",
                    Transaction.BANK_TRANSFER: "Bank transfer",
                    Transaction.NGN_WALLET: "NGN wallet",
                }
                payment_method_name = pm_map.get(transaction.payment_method, "NGN Wallet")

                extra_ctx = {
                    "template_name": "emails/buy_transaction_completed.html",
                    "text_template_name": "emails/buy_transaction_completed.txt",
                    "crypto_amount": f"{transaction.crypto_amount:g}" if isinstance(transaction.crypto_amount, decimal.Decimal) else f"{transaction.crypto_amount}",
                    "asset_code": asset_code,
                    "naira_amount": f"{transaction.naira_amount:,.2f}",
                    "formatted_date": formatted_date,
                    "reference": transaction.id,
                    "asset_symbol": asset_symbol,
                    "usd_value": usd_value,
                    "payment_method": payment_method_name,
                    "cta_url": "https://cheeseballapp.com/dashboard/wallets",
                    "secondary_cta_url": "https://cheeseballapp.com/dashboard/buy",
                }
                notify(
                    transaction.user,
                    title="Buy Crypto — Transaction Confirmed",
                    message=f"You bought {transaction.crypto_amount} {asset_code} successfully — transaction completed.",
                    notification_type=Notification.TRANSACTION_COMPLETED,
                    reference_id=transaction.id,
                    reference_type="Transaction",
                    extra_context=extra_ctx,
                )
            else:
                notify(
                    transaction.user,
                    title=f"{txn_type} Order Completed",
                    message=f"Your {txn_type.lower()} order for {amount} {asset_code} has been completed successfully.",
                    notification_type=Notification.TRANSACTION_COMPLETED,
                    reference_id=transaction.id,
                    reference_type="Transaction",
                )
    elif status == Transaction.FAILED:
        if transaction.transaction_type == Transaction.SELL:
            import decimal
            from django.utils import timezone
            local_dt = timezone.localtime(transaction.failed_at or transaction.updated_at or timezone.now())
            formatted_date = local_dt.strftime("%m/%d/%Y, %I:%M %p")
            symbols_map = {
                "USDT": "₮",
                "BTC": "₿",
                "ETH": "Ξ",
                "SOL": "S",
                "USDC": "$",
            }
            asset_symbol = symbols_map.get(asset_code.upper(), asset_code[0] if asset_code else "")
            usd_value = None
            if transaction.crypto_usd_price:
                usd_amt = transaction.crypto_amount * transaction.crypto_usd_price
                usd_value = f"{usd_amt:,.2f}"

            reason = transaction.fail_reason or "Transaction failed"
            if reason == "expired":
                reason = "Transaction expired — crypto was not received within 24 hours."

            extra_ctx = {
                "template_name": "emails/sell_transaction_failed.html",
                "text_template_name": "emails/sell_transaction_failed.txt",
                "crypto_amount": f"{transaction.crypto_amount:g}" if isinstance(transaction.crypto_amount, decimal.Decimal) else f"{transaction.crypto_amount}",
                "asset_code": asset_code,
                "formatted_date": formatted_date,
                "reference": transaction.id,
                "asset_symbol": asset_symbol,
                "usd_value": usd_value,
                "reason": reason,
                "status_title": "Failed",
                "cta_url": "https://cheeseballapp.com/dashboard/sell",
                "secondary_cta_url": "https://cheeseballapp.com/dashboard",
            }
            notify(
                transaction.user,
                title="Sell Crypto — Transaction Failed",
                message=f"Your sell order for {transaction.crypto_amount} {asset_code} has failed. Reason: {reason}",
                notification_type=Notification.TRANSACTION_FAILED,
                reference_id=transaction.id,
                reference_type="Transaction",
                extra_context=extra_ctx,
            )
        else:
            if transaction.transaction_type == Transaction.BUY:
                import decimal
                from django.utils import timezone
                local_dt = timezone.localtime(transaction.failed_at or transaction.updated_at or timezone.now())
                formatted_date = local_dt.strftime("%m/%d/%Y, %I:%M %p")
                symbols_map = {
                    "USDT": "₮",
                    "BTC": "₿",
                    "ETH": "Ξ",
                    "SOL": "S",
                    "USDC": "$",
                }
                asset_symbol = symbols_map.get(asset_code.upper(), asset_code[0] if asset_code else "")
                usd_value = None
                if transaction.crypto_usd_price:
                    usd_amt = transaction.crypto_amount * transaction.crypto_usd_price
                    usd_value = f"{usd_amt:,.2f}"
                buy_fail_reason = transaction.fail_reason or "Transaction failed"
                pm_map = {
                    Transaction.PAYSTACK: "Paystack",
                    Transaction.BANK_TRANSFER: "Bank transfer",
                    Transaction.NGN_WALLET: "NGN wallet",
                }
                payment_method_name = pm_map.get(transaction.payment_method, "NGN Wallet")
                extra_ctx = {
                    "template_name": "emails/buy_transaction_failed.html",
                    "text_template_name": "emails/buy_transaction_failed.txt",
                    "crypto_amount": f"{transaction.crypto_amount:g}" if isinstance(transaction.crypto_amount, decimal.Decimal) else f"{transaction.crypto_amount}",
                    "asset_code": asset_code,
                    "formatted_date": formatted_date,
                    "reference": transaction.id,
                    "asset_symbol": asset_symbol,
                    "usd_value": usd_value,
                    "reason": buy_fail_reason,
                    "payment_method": payment_method_name,
                    "status_title": "Failed",
                    "cta_url": "https://cheeseballapp.com/dashboard/buy",
                    "secondary_cta_url": "https://cheeseballapp.com/dashboard",
                }
                notify(
                    transaction.user,
                    title="Buy Crypto — Transaction Failed",
                    message=f"Your buy order for {transaction.crypto_amount} {asset_code} has failed. Reason: {buy_fail_reason}",
                    notification_type=Notification.TRANSACTION_FAILED,
                    reference_id=transaction.id,
                    reference_type="Transaction",
                    extra_context=extra_ctx,
                )
            else:
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
        if transaction.transaction_type == Transaction.SELL:
            import decimal
            from django.utils import timezone
            local_dt = timezone.localtime(transaction.reviewed_at or transaction.updated_at or timezone.now())
            formatted_date = local_dt.strftime("%m/%d/%Y, %I:%M %p")
            symbols_map = {
                "USDT": "₮",
                "BTC": "₿",
                "ETH": "Ξ",
                "SOL": "S",
                "USDC": "$",
            }
            asset_symbol = symbols_map.get(asset_code.upper(), asset_code[0] if asset_code else "")
            usd_value = None
            if transaction.crypto_usd_price:
                usd_amt = transaction.crypto_amount * transaction.crypto_usd_price
                usd_value = f"{usd_amt:,.2f}"

            extra_ctx = {
                "template_name": "emails/sell_transaction_failed.html",
                "text_template_name": "emails/sell_transaction_failed.txt",
                "crypto_amount": f"{transaction.crypto_amount:g}" if isinstance(transaction.crypto_amount, decimal.Decimal) else f"{transaction.crypto_amount}",
                "asset_code": asset_code,
                "formatted_date": formatted_date,
                "reference": transaction.id,
                "asset_symbol": asset_symbol,
                "usd_value": usd_value,
                "reason": reason,
                "status_title": "Rejected",
                "cta_url": "https://cheeseballapp.com/dashboard/sell",
                "secondary_cta_url": "https://cheeseballapp.com/dashboard",
            }
            notify(
                transaction.user,
                title="Sell Crypto — Transaction Rejected",
                message=f"Your sell order for {transaction.crypto_amount} {asset_code} was rejected. Reason: {reason}",
                notification_type=Notification.TRANSACTION_REJECTED,
                reference_id=transaction.id,
                reference_type="Transaction",
                extra_context=extra_ctx,
            )
        else:
            if transaction.transaction_type == Transaction.BUY:
                import decimal
                from django.utils import timezone
                local_dt = timezone.localtime(transaction.reviewed_at or transaction.updated_at or timezone.now())
                formatted_date = local_dt.strftime("%m/%d/%Y, %I:%M %p")
                symbols_map = {
                    "USDT": "₮",
                    "BTC": "₿",
                    "ETH": "Ξ",
                    "SOL": "S",
                    "USDC": "$",
                }
                asset_symbol = symbols_map.get(asset_code.upper(), asset_code[0] if asset_code else "")
                usd_value = None
                if transaction.crypto_usd_price:
                    usd_amt = transaction.crypto_amount * transaction.crypto_usd_price
                    usd_value = f"{usd_amt:,.2f}"
                pm_map = {
                    Transaction.PAYSTACK: "Paystack",
                    Transaction.BANK_TRANSFER: "Bank transfer",
                    Transaction.NGN_WALLET: "NGN wallet",
                }
                payment_method_name = pm_map.get(transaction.payment_method, "NGN Wallet")
                extra_ctx = {
                    "template_name": "emails/buy_transaction_failed.html",
                    "text_template_name": "emails/buy_transaction_failed.txt",
                    "crypto_amount": f"{transaction.crypto_amount:g}" if isinstance(transaction.crypto_amount, decimal.Decimal) else f"{transaction.crypto_amount}",
                    "asset_code": asset_code,
                    "formatted_date": formatted_date,
                    "reference": transaction.id,
                    "asset_symbol": asset_symbol,
                    "usd_value": usd_value,
                    "reason": reason,
                    "payment_method": payment_method_name,
                    "status_title": "Rejected",
                    "cta_url": "https://cheeseballapp.com/dashboard/buy",
                    "secondary_cta_url": "https://cheeseballapp.com/dashboard",
                }
                notify(
                    transaction.user,
                    title="Buy Crypto — Transaction Rejected",
                    message=f"Your buy order for {transaction.crypto_amount} {asset_code} was rejected. Reason: {reason}",
                    notification_type=Notification.TRANSACTION_REJECTED,
                    reference_id=transaction.id,
                    reference_type="Transaction",
                    extra_context=extra_ctx,
                )
            else:
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
            message=f"You earned \u20a6{REFERRAL_REWARD_NGN:,.0f} because {user.email} completed their first trade.",
            notification_type=Notification.REFERRAL_REWARD,
            extra_context={
                "template_name": "emails/referral_reward.html",
                "text_template_name": "emails/referral_reward.txt",
                "reward_amount": f"\u20a6{REFERRAL_REWARD_NGN:,.0f}",
                "referee_email": user.email,
                "cta_url": "https://cheeseballapp.com/dashboard/referrals",
            },
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
            expires_at=timezone.now() + timedelta(hours=24),
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
        payout_method = getattr(payload, "payout_method", Transaction.PAYOUT_NGN_WALLET)
        crypto_source = getattr(payload, "crypto_source", Transaction.CRYPTO_SOURCE_EXTERNAL)
        beneficiary = None

        if payout_method != Transaction.PAYOUT_NGN_WALLET:
            raise ValidationError("payout_method must be ngn_wallet")

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
            except Exception as exc:
                logger.exception("Failed to create Quidax deposit wallet for sell — will use PENDING status")
                # Create a PENDING wallet address record so the transaction can proceed.
                # The frontend will poll and the webhook will update the address when Quidax responds.
                from quidax.services import ensure_sub_account
                from quidax.models import QuidaxWalletAddress, QuidaxSubAccount
                try:
                    sub_account = ensure_sub_account(user)
                    quidax_wallet_address_obj, _ = QuidaxWalletAddress.objects.get_or_create(
                        user=user,
                        currency=quote.asset.code.upper(),
                        network=selected_network,
                        defaults={
                            "sub_account": sub_account,
                            "address": "",
                            "status": QuidaxWalletAddress.PENDING,
                            "provider_payload": {"error": str(exc)},
                        },
                    )
                except Exception:
                    logger.exception("Failed to create PENDING Quidax wallet address record")
                broker_wallet_address = ""
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
            expires_at=timezone.now() + timedelta(hours=24),
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

            platform_reserve.balance += transaction_obj.crypto_amount
            platform_reserve.save(update_fields=["balance"])
            ReserveMovement.objects.create(asset=asset, movement_type=ReserveMovement.IN, amount=transaction_obj.crypto_amount, notes=f"Sell {transaction_obj.id}")

        else:
            raise ValidationError("Unknown transaction type for finalization")

        transaction_obj.finalized = True
        transaction_obj.save(update_fields=["finalized"])


def expire_stale_transactions() -> int:
    """
    Mark PENDING_PAYMENT transactions as FAILED (reason: expired) when they have
    crossed their 24-hour window.

    Handles two cases:
      1. New transactions  → have an explicit expires_at field; expire when that passes.
      2. Legacy records    → created before the expires_at field was added (expires_at IS NULL);
                             expire when created_at is more than 24 hours ago.

    This function is called inline from the list_transactions view so that no cron
    job or Celery worker is required — it fires naturally on every user request.
    """
    now = timezone.now()
    cutoff = now - timedelta(hours=24)

    stale_qs = Transaction.objects.filter(
        status=Transaction.PENDING_PAYMENT
    ).filter(
        # Case 1: new transactions with an explicit expiry timestamp
        Q(expires_at__isnull=False, expires_at__lt=now)
        # Case 2: legacy records without an expiry — use created_at as the reference
        | Q(expires_at__isnull=True, created_at__lt=cutoff)
    )

    count = 0
    for txn in stale_qs:
        try:
            transition_transaction(
                txn,
                Transaction.FAILED,
                reason="Transaction expired — crypto was not received within 24 hours.",
                fail_reason="expired",
            )
            count += 1
        except Exception:
            logger.exception("Failed to auto-expire transaction %s", txn.id)

    return count
