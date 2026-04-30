from uuid import UUID

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from ninja.responses import Response

from rates.models import Asset
from rates.services import quantize_naira

from .models import RateLock, WalletBalance, Withdrawal
from .schemas import WithdrawalActionSchema
from .services import (
    build_conversion_quote,
    cancel_withdrawal,
    complete_withdrawal,
    create_rate_lock,
    create_withdrawal,
    estimate_wallet_value_ngn,
    get_user_wallet,
    initialize_wallet_balances,
    perform_conversion,
)
from .models import PlatformAccount, DepositTransaction, PlatformReserve, ReserveMovement
from .schemas import (
    DepositCreateSchema,
    DepositResponseSchema,
    DepositDetailSchema,
    AdminDepositCompleteSchema,
)
from django.db import transaction
from django.utils import timezone
import secrets
import re


def _generate_reference_code(length: int = 10) -> str:

    token = secrets.token_urlsafe(8)
    cleaned = re.sub(r"[^A-Za-z0-9]", "", token).upper()
    if len(cleaned) >= length:
        return cleaned[:length]

    while len(cleaned) < length:
        cleaned += secrets.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    return cleaned


def create_deposit(request, payload: DepositCreateSchema):
    asset = get_object_or_404(Asset, code=payload.asset)
    platform_account = get_object_or_404(PlatformAccount, asset=asset)


    for _ in range(5):
        ref = _generate_reference_code()
        if not DepositTransaction.objects.filter(reference_code=ref).exists():
            break
    else:
        return Response({"detail": "Could not generate unique reference"}, status=500)

    deposit = DepositTransaction.objects.create(
        user=request.auth,
        platform_account=platform_account,
        expected_amount=payload.expected_amount,
        reference_code=ref,
    )

    memo_supported_networks = {"SOL", "XRP", "TRON", "TRX", "USDT"}
    memo_supported = (platform_account.network or "").upper() in memo_supported_networks


    if not platform_account.platform_address:
        return Response({"detail": "This asset is temporarily unavailable for deposits."}, status=400)

    return {
        "id": deposit.id,
        "asset": asset.code,
        "expected_amount": deposit.expected_amount,
        "platform_address": platform_account.platform_address,
        "reference_code": deposit.reference_code,
        "network": platform_account.network,
        "memo_supported": memo_supported,
        "created_at": deposit.created_at.isoformat(),
    }


def get_deposit(request, deposit_id: UUID):
    deposit = get_object_or_404(DepositTransaction, id=deposit_id)
    if not request.auth.is_staff and deposit.user_id != request.auth.id:
        return Response({"detail": "Deposit not found"}, status=404)

    return {
        "id": deposit.id,
        "asset": deposit.platform_account.asset.code,
        "expected_amount": deposit.expected_amount,
        "actual_amount": deposit.actual_amount,
        "platform_address": deposit.platform_account.platform_address,
        "reference_code": deposit.reference_code,
        "external_reference": deposit.external_reference,
        "status": deposit.status,
        "created_at": deposit.created_at.isoformat(),
        "completed_at": deposit.completed_at.isoformat() if deposit.completed_at else None,
    }


def admin_list_deposits(request, status: str | None = None):
    from broker.services import ensure_admin

    ensure_admin(request.auth)
    query = DepositTransaction.objects.all()
    if status:
        query = query.filter(status=status)
    results = []
    for deposit in query.order_by("-created_at"):
        results.append(
            {
                "id": deposit.id,
                "asset": deposit.platform_account.asset.code,
                "expected_amount": deposit.expected_amount,
                "actual_amount": deposit.actual_amount,
                "platform_address": deposit.platform_account.platform_address,
                "reference_code": deposit.reference_code,
                "external_reference": deposit.external_reference,
                "status": deposit.status,
                "created_at": deposit.created_at.isoformat(),
                "completed_at": deposit.completed_at.isoformat() if deposit.completed_at else None,
                "user": {"id": deposit.user.id, "email": deposit.user.email},
            }
        )
    return results


def admin_complete_deposit(request, deposit_id: UUID, payload: AdminDepositCompleteSchema):
    from broker.services import ensure_admin

    ensure_admin(request.auth)
    deposit = get_object_or_404(DepositTransaction, id=deposit_id)
    if deposit.status != DepositTransaction.PENDING:
        return Response({"detail": f"Cannot complete deposit with status {deposit.status}"}, status=400)

    actual_amount = payload.actual_amount

    try:
        with transaction.atomic():

            asset = deposit.platform_account.asset
            from .services import deposit_to_wallet

            wallet = deposit_to_wallet(deposit.user, asset, actual_amount, notes=f"Deposit {deposit.reference_code}")


            platform_reserve, _ = PlatformReserve.objects.get_or_create(asset=asset)
            platform_reserve.balance = platform_reserve.balance + actual_amount
            platform_reserve.save(update_fields=["balance", "updated_at"]) if hasattr(platform_reserve, "updated_at") else platform_reserve.save()

            ReserveMovement.objects.create(asset=asset, movement_type=ReserveMovement.IN, amount=actual_amount, notes=f"Deposit {deposit.reference_code}")

            deposit.actual_amount = actual_amount
            deposit.external_reference = payload.external_reference or ""
            deposit.status = DepositTransaction.COMPLETED
            deposit.completed_at = timezone.now()
            deposit.save()

    except ValidationError as e:
        return Response({"detail": str(e)}, status=400)

    return {
        "id": deposit.id,
        "asset": deposit.platform_account.asset.code,
        "expected_amount": deposit.expected_amount,
        "actual_amount": deposit.actual_amount,
        "platform_address": deposit.platform_account.platform_address,
        "reference_code": deposit.reference_code,
        "external_reference": deposit.external_reference,
        "status": deposit.status,
        "created_at": deposit.created_at.isoformat(),
        "completed_at": deposit.completed_at.isoformat() if deposit.completed_at else None,
    }


def preview_conversion(request, payload):
    from_asset = get_object_or_404(Asset, code=payload.from_asset)
    to_asset = get_object_or_404(Asset, code=payload.to_asset)

    if from_asset.code == to_asset.code:
        return Response({"detail": "Cannot convert to same asset"}, status=400)

    try:
        quote = build_conversion_quote(
            from_asset=from_asset,
            to_asset=to_asset,
            from_amount=payload.from_amount,
        )
        rate_lock = create_rate_lock(
            user=request.auth,
            from_asset=from_asset,
            to_asset=to_asset,
            from_amount=quote["from_amount"],
            to_amount=quote["to_amount"],
            rate=quote["rate"],
            markup_percent=quote["markup_percent"],
            ttl_seconds=60,
        )
        return {
            "rate_lock_id": rate_lock.id,
            "from_asset": rate_lock.from_asset.code,
            "to_asset": rate_lock.to_asset.code,
            "from_amount": rate_lock.from_amount,
            "to_amount": rate_lock.to_amount,
            "rate": rate_lock.rate,
            "markup_percent": rate_lock.markup_percent,
            "expires_at": rate_lock.expires_at.isoformat(),
        }
    except ValidationError as e:
        return Response({"detail": str(e)}, status=400)


def execute_conversion(request, payload):
    rate_lock = get_object_or_404(RateLock, id=payload.rate_lock_id, user=request.auth)

    if rate_lock.is_expired:
        return Response({"detail": "Rate lock has expired"}, status=400)

    try:
        conversion = perform_conversion(request.auth, rate_lock)
        return {
            "id": conversion.id,
            "from_asset": conversion.from_asset.code,
            "to_asset": conversion.to_asset.code,
            "from_amount": conversion.from_amount,
            "to_amount": conversion.to_amount,
            "rate": conversion.rate,
            "markup_percent": conversion.markup_percent,
            "status": conversion.status,
            "created_at": conversion.created_at.isoformat(),
            "completed_at": conversion.completed_at.isoformat() if conversion.completed_at else None,
        }
    except ValidationError as e:
        return Response({"detail": str(e)}, status=400)


def initiate_withdrawal(request, payload):
    asset = get_object_or_404(Asset, code=payload.asset)

    try:
        withdrawal = create_withdrawal(
            user=request.auth,
            asset=asset,
            amount=payload.amount,
            bank_name=payload.bank_name or "",
            bank_account_name=payload.bank_account_name or "",
            bank_account_number=payload.bank_account_number or "",
            wallet_address=payload.wallet_address or "",
            network=payload.network or "",
        )
        return serialize_withdrawal(withdrawal)
    except ValidationError as e:
        return Response({"detail": str(e)}, status=400)


def list_withdrawals(request):
    withdrawals = Withdrawal.objects.filter(user=request.auth) if not request.auth.is_staff else Withdrawal.objects.all()
    return [serialize_withdrawal(withdrawal) for withdrawal in withdrawals]


def get_withdrawal(request, withdrawal_id: UUID):
    withdrawal = get_object_or_404(Withdrawal, id=withdrawal_id)
    if not request.auth.is_staff and withdrawal.user_id != request.auth.id:
        return Response({"detail": "Withdrawal not found"}, status=404)
    return serialize_withdrawal(withdrawal)


def approve_withdrawal(request, withdrawal_id: UUID, payload: WithdrawalActionSchema):
    from broker.services import ensure_admin

    ensure_admin(request.auth)
    withdrawal = get_object_or_404(Withdrawal, id=withdrawal_id)

    if withdrawal.status != Withdrawal.PENDING:
        return Response({"detail": f"Cannot approve withdrawal with status {withdrawal.status}"}, status=400)

    try:
        withdrawal = complete_withdrawal(withdrawal, request.auth)
        withdrawal.admin_notes = payload.note or ""
        withdrawal.save()
    except ValidationError as e:
        return Response({"detail": str(e)}, status=400)

    return serialize_withdrawal(withdrawal)


def reject_withdrawal(request, withdrawal_id: UUID, payload):
    from broker.services import ensure_admin

    ensure_admin(request.auth)
    withdrawal = get_object_or_404(Withdrawal, id=withdrawal_id)

    if withdrawal.status != Withdrawal.PENDING:
        return Response({"detail": f"Cannot reject withdrawal with status {withdrawal.status}"}, status=400)

    try:
        cancel_withdrawal(withdrawal)
        withdrawal.rejection_reason = payload.reason if hasattr(payload, "reason") else payload.note or ""
        withdrawal.save()
    except ValidationError as e:
        return Response({"detail": str(e)}, status=400)

    return {
        "id": withdrawal.id,
        "asset": withdrawal.asset.code,
        "amount": withdrawal.amount,
        "status": withdrawal.status,
        "rejection_reason": withdrawal.rejection_reason,
    }


def get_user_wallets(request, all: bool = False):
    if WalletBalance.objects.filter(user=request.auth).count() == 0:
        initialize_wallet_balances(request.auth)
    top_5_codes = ["USDT", "NGN", "ETH", "BTC", "SOL"]
    query = WalletBalance.objects.filter(user=request.auth)
    if not all:
        query = query.filter(asset__code__in=top_5_codes)
    wallets = query.order_by("asset__code")
    return {
        "balances": [
            {
                "asset": wallet.asset.code,
                "balance": str(wallet.balance),
                "locked_balance": str(wallet.locked_balance),
                "available_balance": str(wallet.available_balance),
            }
            for wallet in wallets
        ]
    }


def get_wallet_balance(request, asset_code: str):
    if WalletBalance.objects.filter(user=request.auth).count() == 0:
        initialize_wallet_balances(request.auth)
    asset = get_object_or_404(Asset, code=asset_code)
    wallet = get_user_wallet(request.auth, asset)
    return {
        "asset": wallet.asset.code,
        "balance": str(wallet.balance),
        "locked_balance": str(wallet.locked_balance),
        "available_balance": str(wallet.available_balance),
    }


def get_balance_summary(request):
    if WalletBalance.objects.filter(user=request.auth).count() == 0:
        initialize_wallet_balances(request.auth)
    top_5_codes = ["USDT", "NGN", "ETH", "BTC", "SOL"]
    wallets = list(WalletBalance.objects.filter(user=request.auth).filter(asset__code__in=top_5_codes))
    ngn_wallet = next((wallet for wallet in wallets if wallet.asset.code == "NGN"), None)

    wallet_valuations = [estimate_wallet_value_ngn(wallet) for wallet in wallets]
    estimated_portfolio_value = sum(valuation["balance_value"] for valuation in wallet_valuations)
    estimated_locked_value = sum(valuation["locked_value"] for valuation in wallet_valuations)
    estimated_available_value = sum(valuation["available_value"] for valuation in wallet_valuations)

    ngn_wallet_balance = quantize_naira(ngn_wallet.balance) if ngn_wallet else quantize_naira(0)
    ngn_wallet_locked_balance = quantize_naira(ngn_wallet.locked_balance) if ngn_wallet else quantize_naira(0)
    ngn_wallet_available_balance = quantize_naira(ngn_wallet.available_balance) if ngn_wallet else quantize_naira(0)

    return {
        "total_balance": str(estimated_portfolio_value),
        "total_locked": str(estimated_locked_value),
        "total_available": str(estimated_available_value),
        "estimated_portfolio_value": str(estimated_portfolio_value),
        "estimated_locked_value": str(estimated_locked_value),
        "estimated_available_value": str(estimated_available_value),
        "ngn_wallet_balance": str(ngn_wallet_balance),
        "ngn_wallet_locked_balance": str(ngn_wallet_locked_balance),
        "ngn_wallet_available_balance": str(ngn_wallet_available_balance),
        "wallet_count": len(wallets),
    }


def serialize_withdrawal(withdrawal):
    return {
        "id": withdrawal.id,
        "asset": withdrawal.asset.code,
        "amount": withdrawal.amount,
        "status": withdrawal.status,
        "bank_name": withdrawal.bank_name,
        "bank_account_name": withdrawal.bank_account_name,
        "bank_account_number": withdrawal.bank_account_number,
        "wallet_address": withdrawal.wallet_address,
        "network": withdrawal.network,
        "admin_notes": withdrawal.admin_notes,
        "rejection_reason": withdrawal.rejection_reason,
        "created_at": withdrawal.created_at.isoformat(),
        "completed_at": withdrawal.completed_at.isoformat() if withdrawal.completed_at else None,
        "reviewed_at": withdrawal.reviewed_at.isoformat() if withdrawal.reviewed_at else None,
    }
