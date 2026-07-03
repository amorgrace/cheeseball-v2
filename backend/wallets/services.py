from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from rates.models import Asset
from rates.services import (
    PERCENT_DIVISOR,
    fetch_market_rate,
    get_rate_configuration,
    quantize_crypto,
    quantize_naira,
)

from .models import Conversion, Ledger, RateLock, WalletBalance, Withdrawal, PlatformReserve, ReserveMovement


NGN_CODE = "NGN"


@transaction.atomic
def initialize_wallet_balances(user):
    top_5_codes = ["USDT", "NGN", "ETH", "BTC", "SOL"]
    assets = Asset.objects.filter(is_active=True, code__in=top_5_codes)
    wallet_balances = []
    for asset in assets:
        wallet_balance, _created = WalletBalance.objects.get_or_create(
            user=user,
            asset=asset,
            defaults={"balance": 0, "locked_balance": 0},
        )
        wallet_balances.append(wallet_balance)
    return wallet_balances


def get_user_wallet(user, asset: Asset) -> WalletBalance:
    wallet, _created = WalletBalance.objects.get_or_create(
        user=user,
        asset=asset,
        defaults={"balance": 0, "locked_balance": 0},
    )
    return wallet


def record_ledger(user, wallet_balance: WalletBalance, transaction_type: str, amount, reference_id=None, reference_model="", notes=""):

    if reference_model is None:
        reference_model = ""
    return Ledger.objects.create(
        user=user,
        wallet_balance=wallet_balance,
        transaction_type=transaction_type,
        amount=amount,
        balance_before=wallet_balance.balance,
        balance_after=wallet_balance.balance,
        locked_before=wallet_balance.locked_balance,
        locked_after=wallet_balance.locked_balance,
        reference_id=reference_id,
        reference_model=reference_model,
        notes=notes,
    )


def build_conversion_quote(*, from_asset: Asset, to_asset: Asset, from_amount):
    if from_asset.code == to_asset.code:
        raise ValidationError("Cannot convert to same asset")

    if from_asset.code != NGN_CODE and to_asset.code != NGN_CODE:
        raise ValidationError("Only NGN to crypto or crypto to NGN conversions are supported")

    if from_asset.code == NGN_CODE:
        config = get_rate_configuration(to_asset)
        market_rate, _source = fetch_market_rate(to_asset)
        buy_markup = config.buy_markup_percent if config else 0
        final_rate = quantize_naira(market_rate * (Decimal("1") + (buy_markup / PERCENT_DIVISOR)))
        to_amount = quantize_crypto(from_amount / final_rate)
        markup_percent = buy_markup
    else:
        config = get_rate_configuration(from_asset)
        market_rate, _source = fetch_market_rate(from_asset)
        sell_markup = config.sell_markup_percent if config else 0
        final_rate = quantize_naira(market_rate * (Decimal("1") - (sell_markup / PERCENT_DIVISOR)))
        to_amount = quantize_naira(from_amount * final_rate)
        markup_percent = sell_markup

    return {
        "from_amount": quantize_naira(from_amount) if from_asset.code == NGN_CODE else quantize_crypto(from_amount),
        "to_amount": to_amount,
        "rate": final_rate,
        "markup_percent": markup_percent,
    }


def estimate_wallet_value_ngn(wallet_balance: WalletBalance):
    if wallet_balance.asset.code == NGN_CODE:
        return {
            "balance_value": quantize_naira(wallet_balance.balance),
            "locked_value": quantize_naira(wallet_balance.locked_balance),
            "available_value": quantize_naira(wallet_balance.available_balance),
        }

    market_rate, _source = fetch_market_rate(wallet_balance.asset)
    balance_value = quantize_naira(wallet_balance.balance * market_rate)
    locked_value = quantize_naira(wallet_balance.locked_balance * market_rate)
    return {
        "balance_value": balance_value,
        "locked_value": locked_value,
        "available_value": quantize_naira(balance_value - locked_value),
    }


@transaction.atomic
def create_rate_lock(user, from_asset: Asset, to_asset: Asset, from_amount, to_amount, rate, markup_percent, ttl_seconds=60):
    expires_at = timezone.now() + timezone.timedelta(seconds=ttl_seconds)
    return RateLock.objects.create(
        user=user,
        from_asset=from_asset,
        to_asset=to_asset,
        from_amount=from_amount,
        to_amount=to_amount,
        rate=rate,
        markup_percent=markup_percent,
        expires_at=expires_at,
    )


@transaction.atomic
def perform_conversion(user, rate_lock: RateLock) -> Conversion:
    if rate_lock.is_expired:
        raise ValidationError("Rate lock has expired")

    from_wallet = get_user_wallet(user, rate_lock.from_asset)
    to_wallet = get_user_wallet(user, rate_lock.to_asset)

    if from_wallet.available_balance < rate_lock.from_amount:
        raise ValidationError(f"Insufficient balance in {rate_lock.from_asset.code}")

    from_wallet.balance -= rate_lock.from_amount
    to_wallet.balance += rate_lock.to_amount
    from_wallet.save(update_fields=["balance", "updated_at"])
    to_wallet.save(update_fields=["balance", "updated_at"])

    record_ledger(user, from_wallet, Ledger.CONVERSION_DEBIT, rate_lock.from_amount, reference_model="Conversion")
    record_ledger(user, to_wallet, Ledger.CONVERSION_CREDIT, rate_lock.to_amount, reference_model="Conversion")

    return Conversion.objects.create(
        user=user,
        rate_lock=rate_lock,
        from_asset=rate_lock.from_asset,
        to_asset=rate_lock.to_asset,
        from_amount=rate_lock.from_amount,
        to_amount=rate_lock.to_amount,
        rate=rate_lock.rate,
        markup_percent=rate_lock.markup_percent,
        status=Conversion.COMPLETED,
        completed_at=timezone.now(),
    )


@transaction.atomic
def create_withdrawal(user, asset: Asset, amount, bank_name="", bank_account_name="", bank_account_number="", wallet_address="", network=""):
    wallet = get_user_wallet(user, asset)
    if wallet.available_balance < amount:
        raise ValidationError(f"Insufficient balance in {asset.code}")

    withdrawal = Withdrawal.objects.create(
        user=user,
        asset=asset,
        amount=amount,
        status=Withdrawal.PENDING,
        bank_name=bank_name,
        bank_account_name=bank_account_name,
        bank_account_number=bank_account_number,
        wallet_address=wallet_address,
        network=network,
    )

    if asset.code != NGN_CODE:
        if not wallet_address:
            raise ValidationError("Wallet address is required for crypto withdrawals")

        from quidax.services import initiate_crypto_withdrawal
        import logging
        logger = logging.getLogger(__name__)

        try:
            quidax_response = initiate_crypto_withdrawal(
                user,
                currency=asset.code,
                amount=amount,
                fund_uid=wallet_address,
                network=network
            )
            withdrawal.admin_notes = f"Quidax Tx: {quidax_response.get('id') or quidax_response}"
            withdrawal.save(update_fields=["admin_notes"])
            
            complete_withdrawal(withdrawal)
            
        except Exception as e:
            logger.exception("Quidax crypto withdrawal failed")
            withdrawal.rejection_reason = str(e)
            withdrawal.status = Withdrawal.FAILED
            withdrawal.save(update_fields=["rejection_reason", "status"])
            
            # Send Telegram notification about failed crypto withdrawal
            try:
                import html
                from notifications.telegram import send_telegram_alert
                telegram_msg = (
                    f"⚠️ <b>Automated Crypto Withdrawal Failed</b>\n"
                    f"<b>User:</b> {html.escape(user.email)}\n"
                    f"<b>Asset:</b> {html.escape(asset.code)}\n"
                    f"<b>Amount:</b> {amount}\n"
                    f"<b>Error:</b> {html.escape(str(e))}"
                )
                send_telegram_alert(telegram_msg)
            except Exception:
                pass
            
            raise ValidationError(f"External crypto withdrawal failed: {str(e)}")
    else:
        # Send Telegram notification for manual NGN withdrawal
        try:
            import html
            from notifications.telegram import send_telegram_alert
            telegram_msg = (
                f"💸 <b>New Withdrawal Request</b>\n"
                f"<b>User:</b> {html.escape(user.email)}\n"
                f"<b>Amount:</b> ₦{amount:,.2f} NGN\n"
                f"<b>Bank:</b> {html.escape(bank_name)} - {html.escape(bank_account_number)}\n"
                f"<b>Account:</b> {html.escape(bank_account_name)}\n"
                f"<b>Status:</b> Awaiting Manual Approval"
            )
            send_telegram_alert(telegram_msg)
        except Exception:
            pass

    return withdrawal


@transaction.atomic
def complete_withdrawal(withdrawal: Withdrawal, admin_user=None):
    if withdrawal.status != Withdrawal.PENDING:
        raise ValidationError(f"Withdrawal is already {withdrawal.status}")

    wallet = get_user_wallet(withdrawal.user, withdrawal.asset)

    if wallet.available_balance < withdrawal.amount:
        raise ValidationError(f"Insufficient balance in {withdrawal.asset.code} at confirmation time")


    wallet.balance -= withdrawal.amount
    wallet.save(update_fields=["balance", "updated_at"])


    record_ledger(withdrawal.user, wallet, Ledger.WITHDRAWAL_DEBIT, withdrawal.amount, reference_model="Withdrawal")


    platform_reserve, _ = PlatformReserve.objects.get_or_create(asset=withdrawal.asset)
    platform_reserve.balance = platform_reserve.balance - withdrawal.amount
    platform_reserve.save(update_fields=["balance"]) if hasattr(platform_reserve, "updated_at") else platform_reserve.save()

    ReserveMovement.objects.create(asset=withdrawal.asset, movement_type=ReserveMovement.OUT, amount=withdrawal.amount, notes=f"Withdrawal {withdrawal.id}")

    withdrawal.status = Withdrawal.COMPLETED
    withdrawal.completed_at = timezone.now()
    withdrawal.approved_by = admin_user
    withdrawal.reviewed_at = timezone.now()
    withdrawal.save(update_fields=["status", "completed_at", "approved_by", "reviewed_at"])

    # Notify user of instantly processed crypto withdrawals
    if withdrawal.asset.code != NGN_CODE:
        try:
            from notifications.services import notify
            from notifications.models import Notification
            from django.utils import timezone as _tz
            _local_dt = _tz.localtime(withdrawal.completed_at or _tz.now())
            _fdate = _local_dt.strftime("%m/%d/%Y, %I:%M %p")
            _dest = withdrawal.wallet_address or withdrawal.bank_account_number or ""
            notify(
                withdrawal.user,
                title="Withdrawal Processed",
                message=f"Your withdrawal of {withdrawal.amount} {withdrawal.asset.code} has been processed and sent.",
                notification_type=Notification.WITHDRAWAL_APPROVED,
                reference_id=withdrawal.id,
                reference_type="Withdrawal",
                extra_context={
                    "template_name": "emails/withdrawal_approved.html",
                    "text_template_name": "emails/withdrawal_approved.txt",
                    "amount": str(withdrawal.amount),
                    "asset_code": withdrawal.asset.code,
                    "withdrawal_type": "Crypto",
                    "destination": _dest,
                    "formatted_date": _fdate,
                    "cta_url": "https://cheeseballapp.com/dashboard/wallets",
                },
            )
        except Exception:
            pass

    return withdrawal


@transaction.atomic
def cancel_withdrawal(withdrawal: Withdrawal):
    if withdrawal.status != Withdrawal.PENDING:
        raise ValidationError(f"Cannot cancel withdrawal with status {withdrawal.status}")


    withdrawal.status = Withdrawal.CANCELLED
    withdrawal.save(update_fields=["status"])
    return withdrawal


@transaction.atomic
def deposit_to_wallet(user, asset: Asset, amount, notes=""):
    wallet = get_user_wallet(user, asset)
    wallet.balance += amount
    wallet.save(update_fields=["balance", "updated_at"])

    record_ledger(user, wallet, Ledger.WALLET_DEPOSIT, amount, notes=notes)

    # --- Notify user ---
    from notifications.models import Notification
    from notifications.services import notify
    from django.utils import timezone as _tz

    if asset.code == NGN_CODE:
        formatted = f"\u20a6{amount:,.2f}"
    else:
        formatted = f"{amount} {asset.code}"

    _local_dt = _tz.localtime(_tz.now())
    _fdate = _local_dt.strftime("%m/%d/%Y, %I:%M %p")
    _new_balance = wallet.balance
    if asset.code == NGN_CODE:
        _balance_str = f"\u20a6{_new_balance:,.2f}"
    else:
        _balance_str = f"{_new_balance} {asset.code}"

    notify(
        user,
        title="Deposit Received",
        message=f"{formatted} has been credited to your {asset.code} wallet.",
        notification_type=Notification.DEPOSIT_RECEIVED,
        extra_context={
            "template_name": "emails/deposit_received.html",
            "text_template_name": "emails/deposit_received.txt",
            "formatted_amount": formatted,
            "asset_code": asset.code,
            "formatted_date": _fdate,
            "new_balance": _balance_str,
            "cta_url": "https://cheeseballapp.com/dashboard/wallets",
        },
    )

    return wallet
