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
    from quidax.services import ensure_wallet_address

    asset = get_object_or_404(Asset, code=payload.asset)

    # Get or create the PlatformAccount for this asset (used for memo detection)
    platform_account, _ = PlatformAccount.objects.get_or_create(
        asset=asset,
        defaults={"network": asset.network}
    )
    network = platform_account.network or asset.network or ""

    # Generate (or retrieve cached) Quidax wallet address for this user
    import logging
    logger = logging.getLogger(__name__)

    try:
        quidax_wallet = ensure_wallet_address(
            request.auth,
            currency=asset.code,
            network=network,
        )
    except Exception as exc:
        logger.exception("Failed to create Quidax deposit wallet for deposit — will use PENDING status")
        from quidax.services import ensure_sub_account
        from quidax.models import QuidaxWalletAddress
        try:
            sub_account = ensure_sub_account(request.auth)
            quidax_wallet, _ = QuidaxWalletAddress.objects.get_or_create(
                user=request.auth,
                currency=asset.code.upper(),
                network=network,
                defaults={
                    "sub_account": sub_account,
                    "address": "",
                    "status": QuidaxWalletAddress.PENDING,
                    "provider_payload": {"error": str(exc)},
                },
            )
        except Exception:
            logger.exception("Failed to create PENDING Quidax wallet address record")
            return Response({"detail": "Failed to initiate address generation"}, status=500)

    # Generate unique reference code
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
    memo_supported = network.upper() in memo_supported_networks

    return {
        "id": deposit.id,
        "asset": asset.code,
        "expected_amount": deposit.expected_amount,
        "platform_address": quidax_wallet.address,
        "reference_code": quidax_wallet.destination_tag or deposit.reference_code,
        "network": network or quidax_wallet.network,
        "memo_supported": memo_supported or bool(quidax_wallet.destination_tag),
        "created_at": deposit.created_at.isoformat(),
    }



def get_deposit(request, deposit_id: str):
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


def admin_complete_deposit(request, deposit_id: str, payload: AdminDepositCompleteSchema):
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


def fund_ngn_wallet(request, payload):
    from payments.views import create_paystack_charge, _amount_to_kobo
    from .models import WalletFunding

    for _ in range(5):
        reference = f"wf_{_generate_reference_code(12)}"
        if not WalletFunding.objects.filter(reference=reference).exists():
            break
    else:
        return Response({"detail": "Could not generate unique reference"}, status=500)

    try:
        amount_kobo = _amount_to_kobo(payload.amount)
        metadata = {
            "type": "wallet_funding",
        }
        charge_response = create_paystack_charge(
            email=request.auth.email,
            amount_kobo=amount_kobo,
            reference=reference,
            metadata=metadata
        )
    except ValidationError as e:
        return Response({"detail": str(e)}, status=400)

    funding = WalletFunding.objects.create(
        user=request.auth,
        amount=payload.amount,
        reference=reference,
        status=WalletFunding.PENDING,
        provider_payload=charge_response,
    )

    data = charge_response.get("data", {})
    return {
        "id": funding.id,
        "amount": funding.amount,
        "reference": funding.reference,
        "status": funding.status,
        "authorization_url": data.get("authorization_url"),
        "access_code": data.get("access_code"),
        "account_number": data.get("bank_transfer", {}).get("account_number") or data.get("account_number"),
        "bank_name": data.get("bank_transfer", {}).get("bank_name") or data.get("bank_name"),
        "account_name": data.get("bank_transfer", {}).get("account_name") or data.get("account_name"),
        "expires_at": data.get("bank_transfer", {}).get("account_expires_at"),
        "created_at": funding.created_at.isoformat(),
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


# ---------------------------------------------------------------------------
# Treasury sync + reconciliation
# ---------------------------------------------------------------------------

def _is_cron_authenticated(request) -> bool:
    """Allow access if the request carries the server-side CRON_SECRET header."""
    from django.conf import settings
    secret = getattr(settings, "CRON_SECRET", "")
    if not secret:
        return False
    return request.headers.get("X-Cron-Secret", "") == secret


def sync_treasury(request):
    """
    Fetch Quidax master-wallet balances for all active assets and store a
    TreasurySnapshot row for each.  Accepts either:
      - A valid staff JWT (admin triggering it manually), or
      - X-Cron-Secret header (GitHub Actions cron job).
    """
    import logging
    from decimal import Decimal, InvalidOperation

    from rates.models import Asset
    from .models import TreasurySnapshot

    logger = logging.getLogger(__name__)

    # Allow cron header auth as an alternative to JWT staff auth
    if not _is_cron_authenticated(request):
        from broker.services import ensure_admin
        ensure_admin(request.auth)

    assets = Asset.objects.filter(is_active=True).exclude(code="NGN")

    synced = []
    errors = []

    for asset in assets:
        try:
            from quidax.services import _quidax_request
            response = _quidax_request(f"users/me/wallets/{asset.code.lower()}")
            data = response.get("data") or response
            raw_balance = data.get("balance", "0")
            balance = Decimal(str(raw_balance))
            TreasurySnapshot.objects.create(asset=asset, balance=balance, source="quidax")
            synced.append({"asset": asset.code, "balance": str(balance)})
        except (InvalidOperation, Exception) as exc:
            logger.warning("Treasury sync failed for %s: %s", asset.code, exc)
            errors.append({"asset": asset.code, "error": str(exc)})

    return {
        "synced": len(synced),
        "errors": len(errors),
        "results": synced,
        "failures": errors,
    }


def get_reconciliation(request):
    """
    Returns per-asset reconciliation: user liability vs treasury snapshot vs
    platform reserve.  Staff JWT required.
    """
    from decimal import Decimal
    from django.db.models import Sum
    from django.utils import timezone

    from broker.services import ensure_admin
    from rates.models import Asset
    from .models import WalletBalance, PlatformReserve, TreasurySnapshot

    ensure_admin(request.auth)

    assets = Asset.objects.filter(is_active=True).exclude(code="NGN")
    rows = []

    for asset in assets:
        # Sum of all user balances (our liability)
        user_liability = (
            WalletBalance.objects.filter(asset=asset)
            .aggregate(total=Sum("balance"))["total"]
            or Decimal("0")
        )

        # Latest treasury snapshot
        latest_snapshot = (
            TreasurySnapshot.objects.filter(asset=asset).order_by("-synced_at").first()
        )
        treasury_balance = latest_snapshot.balance if latest_snapshot else None
        snapshot_age_seconds = (
            int((timezone.now() - latest_snapshot.synced_at).total_seconds())
            if latest_snapshot
            else None
        )

        # Internal platform reserve (our own ledger tracking)
        try:
            reserve = PlatformReserve.objects.get(asset=asset)
            platform_reserve = reserve.balance
        except PlatformReserve.DoesNotExist:
            platform_reserve = Decimal("0")

        difference = (treasury_balance - user_liability) if treasury_balance is not None else None

        rows.append({
            "asset": asset.code,
            "asset_name": asset.name,
            "user_liability": str(user_liability),
            "treasury_balance": str(treasury_balance) if treasury_balance is not None else None,
            "platform_reserve": str(platform_reserve),
            "difference": str(difference) if difference is not None else None,
            "has_deficit": bool(difference is not None and difference < 0),
            "snapshot_age_seconds": snapshot_age_seconds,
            "withdrawal_mode": asset.withdrawal_mode,
            "send_enabled": asset.send_enabled,
            "deposit_enabled": asset.deposit_enabled,
        })

    return {"assets": rows, "count": len(rows)}

