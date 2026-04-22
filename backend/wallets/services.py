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

from .models import Conversion, Ledger, RateLock, WalletBalance, Withdrawal


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


def record_ledger(user, wallet_balance: WalletBalance, transaction_type: str, amount, reference_id=None, reference_model=None, notes=""):
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

    wallet.locked_balance += amount
    wallet.save(update_fields=["locked_balance", "updated_at"])

    record_ledger(user, wallet, Ledger.WITHDRAWAL_LOCK, amount, reference_model="Withdrawal")

    return Withdrawal.objects.create(
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


@transaction.atomic
def complete_withdrawal(withdrawal: Withdrawal, admin_user=None):
    if withdrawal.status != Withdrawal.PENDING:
        raise ValidationError(f"Withdrawal is already {withdrawal.status}")

    wallet = get_user_wallet(withdrawal.user, withdrawal.asset)
    wallet.balance -= withdrawal.amount
    wallet.locked_balance -= withdrawal.amount
    wallet.save(update_fields=["balance", "locked_balance", "updated_at"])

    record_ledger(withdrawal.user, wallet, Ledger.WITHDRAWAL_DEBIT, withdrawal.amount, reference_model="Withdrawal")

    withdrawal.status = Withdrawal.COMPLETED
    withdrawal.completed_at = timezone.now()
    withdrawal.approved_by = admin_user
    withdrawal.reviewed_at = timezone.now()
    withdrawal.save(update_fields=["status", "completed_at", "approved_by", "reviewed_at"])
    return withdrawal


@transaction.atomic
def cancel_withdrawal(withdrawal: Withdrawal):
    if withdrawal.status != Withdrawal.PENDING:
        raise ValidationError(f"Cannot cancel withdrawal with status {withdrawal.status}")

    wallet = get_user_wallet(withdrawal.user, withdrawal.asset)
    wallet.locked_balance -= withdrawal.amount
    wallet.save(update_fields=["locked_balance", "updated_at"])

    record_ledger(withdrawal.user, wallet, Ledger.WITHDRAWAL_RELEASE, withdrawal.amount, reference_model="Withdrawal")

    withdrawal.status = Withdrawal.CANCELLED
    withdrawal.save(update_fields=["status"])
    return withdrawal


@transaction.atomic
def deposit_to_wallet(user, asset: Asset, amount, notes=""):
    wallet = get_user_wallet(user, asset)
    wallet.balance += amount
    wallet.save(update_fields=["balance", "updated_at"])

    record_ledger(user, wallet, Ledger.WALLET_DEPOSIT, amount, notes=notes)
    return wallet
