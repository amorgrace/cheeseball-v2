import logging
import math
from datetime import timedelta

from django.db.models import Sum, Q, Count
from django.utils import timezone
from ninja import Router, Query
from asgiref.sync import sync_to_async

from engine.admin_auth import AdminJWTAuth
from engine.admin_schemas import (
    AdminDelegateSchema,
    AdminGiftCardApproveSchema,
    AdminGiftCardItem,
    AdminGiftCardListResponse,
    AdminGiftCardRejectSchema,
    AdminKYCItem,
    AdminKYCListResponse,
    AdminKYCReviewSchema,
    AdminLedgerItem,
    AdminLedgerListResponse,
    AdminQuidaxDepositItem,
    AdminQuidaxResponse,
    AdminQuidaxWebhookItem,
    AdminQuidaxWithdrawalItem,
    AdminRateConfigItem,
    AdminRateUpdateSchema,
    AdminReserveItem,
    AdminReserveMovementItem,
    AdminReservesResponse,
    AdminTransactionActionSchema,
    AdminTransactionDetailSchema,
    AdminTransactionItem,
    AdminTransactionListResponse,
    AdminTransactionRejectSchema,
    AdminUserDetailSchema,
    AdminUserListItem,
    AdminUserListResponse,
    AdminUserUpdateSchema,
    AdminWalletItem,
    AdminWalletListResponse,
    AdminWithdrawalActionSchema,
    AdminWithdrawalItem,
    AdminWithdrawalListResponse,
    AdminWithdrawalRejectSchema,
    DashboardStatsSchema,
    MessageSchema,
    PaginatedMeta,
)

logger = logging.getLogger(__name__)

router = Router(tags=["Admin"], auth=AdminJWTAuth())


# ─── Helpers ──────────────────────────────────────────────────────────────────

def paginate_qs(qs, page: int = 1, page_size: int = 25):
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    total = qs.count()
    total_pages = max(1, math.ceil(total / page_size))
    offset = (page - 1) * page_size
    items = list(qs[offset : offset + page_size])
    meta = PaginatedMeta(total=total, page=page, page_size=page_size, total_pages=total_pages)
    return items, meta


# ─── Dashboard Stats ─────────────────────────────────────────────────────────

@router.get("/stats", response=DashboardStatsSchema)
async def dashboard_stats(request):
    from django.core.cache import cache
    cached_stats = cache.get("admin_dashboard_stats")
    if cached_stats is not None:
        return cached_stats

    @sync_to_async
    def _inner():
        from authenticator.models import CustomUser
        from broker.models import Transaction
        from kyc.models import KYCSubmission
        from wallets.models import Withdrawal

        now = timezone.now()
        day_ago = now - timedelta(hours=24)

        total_users = CustomUser.objects.count()
        verified_users = CustomUser.objects.filter(kyc_status=CustomUser.KYC_VERIFIED).count()
        pending_kyc = KYCSubmission.objects.filter(status=KYCSubmission.SUBMITTED).count()
        total_transactions = Transaction.objects.count()
        pending_transactions = Transaction.objects.filter(
            status__in=[Transaction.PENDING_PAYMENT, Transaction.PENDING_REVIEW, Transaction.PAID, Transaction.PROCESSING]
        ).count()
        pending_withdrawals = Withdrawal.objects.filter(status=Withdrawal.PENDING).count()
        total_volume = Transaction.objects.filter(
            status__in=[Transaction.COMPLETED, Transaction.PROCESSING, Transaction.PAID]
        ).aggregate(total=Sum("naira_amount"))["total"] or 0
        volume_24h = Transaction.objects.filter(
            status__in=[Transaction.COMPLETED, Transaction.PROCESSING, Transaction.PAID],
            created_at__gte=day_ago,
        ).aggregate(total=Sum("naira_amount"))["total"] or 0

        return DashboardStatsSchema(
            total_users=total_users,
            verified_users=verified_users,
            pending_kyc=pending_kyc,
            total_transactions=total_transactions,
            pending_transactions=pending_transactions,
            pending_withdrawals=pending_withdrawals,
            total_volume_ngn=total_volume,
            total_volume_24h_ngn=volume_24h,
        )
    result = await _inner()
    cache.set("admin_dashboard_stats", result, 5 * 60)  # Cache for 5 minutes
    return result


# ─── Users ────────────────────────────────────────────────────────────────────

@router.get("/users", response=AdminUserListResponse)
async def list_users(
    request,
    page: int = Query(1),
    page_size: int = Query(25),
    search: str = Query(None),
    kyc_status: str = Query(None),
    is_active: bool = Query(None),
):
    @sync_to_async
    def _inner():
        from authenticator.models import CustomUser

        qs = CustomUser.objects.all().order_by("-date_joined")
        if search:
            qs = qs.filter(Q(email__icontains=search) | Q(first_name__icontains=search) | Q(last_name__icontains=search))
        if kyc_status:
            qs = qs.filter(kyc_status=kyc_status)
        if is_active is not None:
            qs = qs.filter(is_active=is_active)

        items, meta = paginate_qs(qs, page, page_size)
        users = [
            AdminUserListItem(
                id=u.id, email=u.email, first_name=u.first_name, last_name=u.last_name,
                phone_number=u.phone_number, referral_code=u.referral_code,
                kyc_status=u.kyc_status, is_active=u.is_active, is_staff=u.is_staff,
                date_joined=u.date_joined, last_login=u.last_login,
            )
            for u in items
        ]
        return AdminUserListResponse(users=users, meta=meta)
    return await _inner()


@router.post("/users/delegate-admin", response=MessageSchema)
async def delegate_admin(request, payload: AdminDelegateSchema):
    @sync_to_async
    def _inner():
        from authenticator.models import CustomUser

        email = payload.email.strip().lower()
        if not email:
            return 400, MessageSchema(detail="Email is required.")

        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return 400, MessageSchema(detail=f"No account found with email '{email}'. Make sure the user is registered first.")

        if user.is_staff:
            return MessageSchema(detail=f"{user.email} is already an admin.")

        user.is_staff = True
        user.save(update_fields=["is_staff"])
        logger.info(f"Admin {request.auth.email} delegated admin access to {user.email}")

        try:
            import html
            from notifications.telegram import send_telegram_alert
            _ts = timezone.now().strftime("%Y-%m-%d %H:%M UTC")
            telegram_msg = (
                f"⚠️ <b>ADMIN ACCESS GRANTED</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"👮 Action By: {html.escape(request.auth.email)}\n"
                f"👤 Target User: {html.escape(user.email)}\n"
                f"⏰ {_ts}"
            )
            send_telegram_alert(telegram_msg)
        except Exception:
            pass

        return MessageSchema(detail=f"{user.email} is now an admin.")

    return await _inner()


@router.get("/admins", response=AdminUserListResponse)
async def list_admins(
    request,
    page: int = Query(1),
    page_size: int = Query(25),
    search: str = Query(None),
):
    @sync_to_async
    def _inner():
        from authenticator.models import CustomUser

        qs = CustomUser.objects.filter(is_staff=True).order_by("-date_joined")
        if search:
            qs = qs.filter(Q(email__icontains=search) | Q(first_name__icontains=search) | Q(last_name__icontains=search))

        items, meta = paginate_qs(qs, page, page_size)
        admins = [
            AdminUserListItem(
                id=u.id, email=u.email, first_name=u.first_name, last_name=u.last_name,
                phone_number=u.phone_number, referral_code=u.referral_code,
                kyc_status=u.kyc_status, is_active=u.is_active, is_staff=u.is_staff,
                date_joined=u.date_joined, last_login=u.last_login,
            )
            for u in items
        ]
        return AdminUserListResponse(users=admins, meta=meta)

    return await _inner()


@router.post("/admins/revoke", response=MessageSchema)
async def revoke_admin(request, payload: AdminDelegateSchema):
    @sync_to_async
    def _inner():
        from authenticator.models import CustomUser

        email = payload.email.strip().lower()
        if not email:
            return 400, MessageSchema(detail="Email is required.")

        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return 400, MessageSchema(detail=f"No account found with email '{email}'.")

        if user.id == request.auth.id:
            return 400, MessageSchema(detail="You cannot remove your own admin access.")
        if user.is_superuser:
            return 400, MessageSchema(detail=f"{user.email} is a superuser — their access can only be changed via the Django admin panel.")
        if not user.is_staff:
            return MessageSchema(detail=f"{user.email} is not an admin.")

        user.is_staff = False
        user.save(update_fields=["is_staff"])
        logger.info(f"Admin {request.auth.email} removed admin access from {user.email}")

        try:
            import html
            from notifications.telegram import send_telegram_alert
            _ts = timezone.now().strftime("%Y-%m-%d %H:%M UTC")
            telegram_msg = (
                f"⚠️ <b>ADMIN ACCESS REVOKED</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"👮 Action By: {html.escape(request.auth.email)}\n"
                f"👤 Target User: {html.escape(user.email)}\n"
                f"⏰ {_ts}"
            )
            send_telegram_alert(telegram_msg)
        except Exception:
            pass

        return MessageSchema(detail=f"{user.email} is no longer an admin.")

    return await _inner()


@router.get("/users/{user_id}", response=AdminUserDetailSchema)
async def get_user(request, user_id: str):
    @sync_to_async
    def _inner():
        from authenticator.models import CustomUser

        user = CustomUser.objects.get(id=user_id)
        referral_count = user.referrals.count()
        referred_by_email = user.referred_by.email if user.referred_by else None

        return AdminUserDetailSchema(
            id=user.id, email=user.email, first_name=user.first_name, last_name=user.last_name,
            phone_number=user.phone_number, referral_code=user.referral_code,
            referred_by_email=referred_by_email, referral_count=referral_count,
            kyc_status=user.kyc_status, is_active=user.is_active, is_staff=user.is_staff,
            is_superuser=user.is_superuser, verified_at=user.verified_at,
            date_joined=user.date_joined, last_login=user.last_login,
        )
    return await _inner()


@router.patch("/users/{user_id}", response=MessageSchema)
async def update_user(request, user_id: str, payload: AdminUserUpdateSchema):
    @sync_to_async
    def _inner():
        from authenticator.models import CustomUser

        user = CustomUser.objects.get(id=user_id)
        if payload.is_active is not None:
            user.is_active = payload.is_active
        if payload.kyc_status is not None:
            user.kyc_status = payload.kyc_status
        user.save()
        logger.info(f"Admin {request.auth.email} updated user {user.email}: {payload.dict(exclude_none=True)}")
        return MessageSchema(detail="User updated successfully.")
    return await _inner()


# ─── Transactions ─────────────────────────────────────────────────────────────

@router.get("/transactions", response=AdminTransactionListResponse)
async def list_transactions(
    request,
    page: int = Query(1),
    page_size: int = Query(25),
    status: str = Query(None),
    transaction_type: str = Query(None),
    search: str = Query(None),
):
    @sync_to_async
    def _inner():
        from broker.models import Transaction

        qs = Transaction.objects.select_related("user", "asset").all()
        if status:
            qs = qs.filter(status=status)
        if transaction_type:
            qs = qs.filter(transaction_type=transaction_type)
        if search:
            qs = qs.filter(Q(user__email__icontains=search) | Q(id__icontains=search))

        items, meta = paginate_qs(qs, page, page_size)
        transactions = [
            AdminTransactionItem(
                id=t.id, user_email=t.user.email, transaction_type=t.transaction_type,
                asset=t.asset.code, status=t.status, payment_method=t.payment_method,
                naira_amount=t.naira_amount, crypto_amount=t.crypto_amount,
                final_rate=t.final_rate, created_at=t.created_at,
            )
            for t in items
        ]
        return AdminTransactionListResponse(transactions=transactions, meta=meta)
    return await _inner()


@router.get("/transactions/{txn_id}", response=AdminTransactionDetailSchema)
async def get_transaction(request, txn_id: str):
    @sync_to_async
    def _inner():
        from broker.models import Transaction

        t = Transaction.objects.select_related("user", "asset").get(id=txn_id)
        return AdminTransactionDetailSchema(
            id=t.id, user_email=t.user.email, user_id=t.user.id,
            transaction_type=t.transaction_type, asset=t.asset.code, status=t.status,
            payment_method=t.payment_method, crypto_source=t.crypto_source,
            payout_method=t.payout_method, naira_amount=t.naira_amount,
            crypto_amount=t.crypto_amount, market_rate=t.market_rate,
            markup_percent=t.markup_percent, final_rate=t.final_rate,
            crypto_usd_price=t.crypto_usd_price, wallet_address=t.wallet_address,
            network=t.network, broker_wallet_address=t.broker_wallet_address,
            bank_name=t.bank_name, bank_account_name=t.bank_account_name,
            bank_account_number=t.bank_account_number, admin_notes=t.admin_notes,
            rejection_reason=t.rejection_reason, reviewed_at=t.reviewed_at,
            paid_at=t.paid_at, completed_at=t.completed_at, failed_at=t.failed_at,
            created_at=t.created_at, updated_at=t.updated_at,
        )
    return await _inner()


@router.post("/transactions/{txn_id}/approve", response=MessageSchema)
async def approve_transaction(request, txn_id: str, payload: AdminTransactionActionSchema = None):
    @sync_to_async
    def _inner():
        from broker.models import Transaction

        t = Transaction.objects.get(id=txn_id)
        if t.status not in [Transaction.PENDING_REVIEW, Transaction.PAID]:
            return 400, MessageSchema(detail=f"Cannot approve transaction in '{t.status}' status.")
        t.status = Transaction.PROCESSING
        t.approved_by = request.auth
        t.reviewed_at = timezone.now()
        if payload and payload.admin_notes:
            t.admin_notes = payload.admin_notes
        t.save()
        logger.info(f"Admin {request.auth.email} approved transaction {t.id}")
        return MessageSchema(detail="Transaction approved.")
    return await _inner()


@router.post("/transactions/{txn_id}/reject", response=MessageSchema)
async def reject_transaction(request, txn_id: str, payload: AdminTransactionRejectSchema):
    @sync_to_async
    def _inner():
        from broker.models import Transaction

        t = Transaction.objects.get(id=txn_id)
        if t.status in [Transaction.COMPLETED, Transaction.FAILED, Transaction.REJECTED]:
            return 400, MessageSchema(detail=f"Cannot reject transaction in '{t.status}' status.")
        t.status = Transaction.REJECTED
        t.rejection_reason = payload.rejection_reason
        t.approved_by = request.auth
        t.reviewed_at = timezone.now()
        if payload.admin_notes:
            t.admin_notes = payload.admin_notes
        t.save()
        logger.info(f"Admin {request.auth.email} rejected transaction {t.id}")
        return MessageSchema(detail="Transaction rejected.")
    return await _inner()


# ─── KYC ──────────────────────────────────────────────────────────────────────

@router.get("/kyc", response=AdminKYCListResponse)
async def list_kyc(
    request,
    page: int = Query(1),
    page_size: int = Query(25),
    status: str = Query(None),
):
    @sync_to_async
    def _inner():
        from kyc.models import KYCSubmission

        qs = KYCSubmission.objects.select_related("user").all()
        if status:
            qs = qs.filter(status=status)

        items, meta = paginate_qs(qs, page, page_size)
        submissions = [
            AdminKYCItem(
                id=s.id, user_email=s.user.email, user_id=s.user.id,
                id_type=s.id_type, document_url=s.document_url,
                status=s.status, admin_note=s.admin_note,
                reviewed_at=s.reviewed_at, created_at=s.created_at,
            )
            for s in items
        ]
        return AdminKYCListResponse(submissions=submissions, meta=meta)
    return await _inner()


@router.post("/kyc/{kyc_id}/review", response=MessageSchema)
async def review_kyc(request, kyc_id: str, payload: AdminKYCReviewSchema):
    @sync_to_async
    def _inner():
        from authenticator.models import CustomUser
        from kyc.models import KYCSubmission

        submission = KYCSubmission.objects.select_related("user").get(id=kyc_id)
        if submission.status != KYCSubmission.SUBMITTED:
            return 400, MessageSchema(detail=f"Cannot review KYC in '{submission.status}' status.")

        now = timezone.now()
        if payload.action == "approve":
            submission.status = KYCSubmission.VERIFIED
            submission.user.kyc_status = CustomUser.KYC_VERIFIED
        elif payload.action == "reject":
            submission.status = KYCSubmission.REJECTED
            submission.user.kyc_status = CustomUser.KYC_REJECTED
        else:
            return 400, MessageSchema(detail="Action must be 'approve' or 'reject'.")

        submission.reviewed_by = request.auth
        submission.reviewed_at = now
        if payload.admin_note:
            submission.admin_note = payload.admin_note
        submission.save()
        submission.user.save()
        logger.info(f"Admin {request.auth.email} {payload.action}d KYC {kyc_id} for {submission.user.email}")

        try:
            import html
            from notifications.telegram import send_telegram_alert
            action_icon = "✅" if payload.action == "approve" else "❌"
            action_label = "KYC APPROVED" if payload.action == "approve" else "KYC REJECTED"
            _ts = timezone.now().strftime("%Y-%m-%d %H:%M UTC")
            telegram_msg = (
                f"{action_icon} <b>{action_label}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 User: {html.escape(submission.user.email)}\n"
                f"👮 Action By: {html.escape(request.auth.email)}\n"
                f"📝 Note: {html.escape(payload.admin_note or 'None')}\n"
                f"⏰ {_ts}"
            )
            send_telegram_alert(telegram_msg)
        except Exception:
            pass

        # --- Notify user ---
        from notifications.models import Notification
        from notifications.services import notify
        if payload.action == "approve":
            notify(
                submission.user,
                title="KYC Approved",
                message="Your identity verification has been approved. You now have full access to all features.",
                notification_type=Notification.KYC_APPROVED,
                reference_id=submission.id,
                reference_type="KYCSubmission",
                extra_context={
                    "template_name": "emails/kyc_approved.html",
                    "text_template_name": "emails/kyc_approved.txt",
                    "cta_url": "https://cheeseballapp.com/dashboard",
                },
            )
        else:
            note_text = payload.admin_note or "No reason provided."
            notify(
                submission.user,
                title="KYC Rejected",
                message=f"Your identity verification was rejected. Reason: {note_text}. Please resubmit.",
                notification_type=Notification.KYC_REJECTED,
                reference_id=submission.id,
                reference_type="KYCSubmission",
                extra_context={
                    "template_name": "emails/kyc_rejected.html",
                    "text_template_name": "emails/kyc_rejected.txt",
                    "reason": note_text,
                    "cta_url": "https://cheeseballapp.com/dashboard/kyc",
                },
            )

        return MessageSchema(detail=f"KYC {payload.action}d successfully.")
    return await _inner()


# ─── Withdrawals ──────────────────────────────────────────────────────────────

@router.get("/withdrawals", response=AdminWithdrawalListResponse)
async def list_withdrawals(
    request,
    page: int = Query(1),
    page_size: int = Query(25),
    status: str = Query(None),
):
    @sync_to_async
    def _inner():
        from wallets.models import Withdrawal

        qs = Withdrawal.objects.select_related("user", "asset").all()
        if status:
            qs = qs.filter(status=status)

        items, meta = paginate_qs(qs, page, page_size)
        withdrawals = [
            AdminWithdrawalItem(
                id=w.id, user_email=w.user.email, user_id=w.user.id,
                asset=w.asset.code, amount=w.amount, status=w.status,
                bank_name=w.bank_name, bank_account_name=w.bank_account_name,
                bank_account_number=w.bank_account_number,
                wallet_address=w.wallet_address, network=w.network,
                created_at=w.created_at,
            )
            for w in items
        ]
        return AdminWithdrawalListResponse(withdrawals=withdrawals, meta=meta)
    return await _inner()


@router.post("/withdrawals/{withdrawal_id}/approve", response=MessageSchema)
async def approve_withdrawal(request, withdrawal_id: str, payload: AdminWithdrawalActionSchema = None):
    @sync_to_async
    def _inner():
        from wallets.models import Withdrawal

        w = Withdrawal.objects.get(id=withdrawal_id)
        if w.status != Withdrawal.PENDING:
            return 400, MessageSchema(detail=f"Cannot approve withdrawal in '{w.status}' status.")
        w.status = Withdrawal.COMPLETED
        w.approved_by = request.auth
        w.reviewed_at = timezone.now()
        w.completed_at = timezone.now()
        if payload and payload.admin_notes:
            w.admin_notes = payload.admin_notes
        w.save()
        logger.info(f"Admin {request.auth.email} approved withdrawal {w.id}")

        # --- Notify user ---
        from notifications.models import Notification
        from notifications.services import notify
        from django.utils import timezone as _tz
        _fdate = _tz.localtime(w.completed_at or _tz.now()).strftime("%m/%d/%Y, %I:%M %p")
        _dest = w.bank_account_number or w.wallet_address or ""
        notify(
            w.user,
            title="Withdrawal Approved",
            message=f"Your withdrawal of {w.amount} {w.asset.code} has been approved and is being processed.",
            notification_type=Notification.WITHDRAWAL_APPROVED,
            reference_id=w.id,
            reference_type="Withdrawal",
            extra_context={
                "template_name": "emails/withdrawal_approved.html",
                "text_template_name": "emails/withdrawal_approved.txt",
                "amount": str(w.amount),
                "asset_code": w.asset.code,
                "withdrawal_type": "NGN" if w.asset.code == "NGN" else "Crypto",
                "destination": _dest,
                "formatted_date": _fdate,
                "cta_url": "https://cheeseballapp.com/dashboard/wallets",
            },
        )

        return MessageSchema(detail="Withdrawal approved.")
    return await _inner()


@router.post("/withdrawals/{withdrawal_id}/reject", response=MessageSchema)
async def reject_withdrawal(request, withdrawal_id: str, payload: AdminWithdrawalRejectSchema):
    @sync_to_async
    def _inner():
        from wallets.models import Withdrawal

        w = Withdrawal.objects.get(id=withdrawal_id)
        if w.status != Withdrawal.PENDING:
            return 400, MessageSchema(detail=f"Cannot reject withdrawal in '{w.status}' status.")
        w.status = Withdrawal.FAILED
        w.rejection_reason = payload.rejection_reason
        w.approved_by = request.auth
        w.reviewed_at = timezone.now()
        w.failed_at = timezone.now()
        if payload.admin_notes:
            w.admin_notes = payload.admin_notes
        w.save()
        logger.info(f"Admin {request.auth.email} rejected withdrawal {w.id}")

        # --- Notify user ---
        from notifications.models import Notification
        from notifications.services import notify
        from django.utils import timezone as _tz
        reason = payload.rejection_reason or "No reason provided."
        _fdate = _tz.localtime(w.failed_at or _tz.now()).strftime("%m/%d/%Y, %I:%M %p")
        notify(
            w.user,
            title="Withdrawal Rejected",
            message=f"Your withdrawal of {w.amount} {w.asset.code} was rejected. Reason: {reason}",
            notification_type=Notification.WITHDRAWAL_REJECTED,
            reference_id=w.id,
            reference_type="Withdrawal",
            extra_context={
                "template_name": "emails/withdrawal_rejected.html",
                "text_template_name": "emails/withdrawal_rejected.txt",
                "amount": str(w.amount),
                "asset_code": w.asset.code,
                "reason": reason,
                "formatted_date": _fdate,
                "cta_url": "https://cheeseballapp.com/dashboard/wallets",
            },
        )

        return MessageSchema(detail="Withdrawal rejected.")
    return await _inner()


# ─── Wallets ──────────────────────────────────────────────────────────────────

@router.get("/wallets", response=AdminWalletListResponse)
async def list_wallets(
    request,
    page: int = Query(1),
    page_size: int = Query(25),
    search: str = Query(None),
    asset: str = Query(None),
):
    @sync_to_async
    def _inner():
        from wallets.models import WalletBalance

        qs = WalletBalance.objects.select_related("user", "asset").all()
        if search:
            qs = qs.filter(user__email__icontains=search)
        if asset:
            qs = qs.filter(asset__code=asset)

        items, meta = paginate_qs(qs, page, page_size)
        wallets = [
            AdminWalletItem(
                id=w.id, user_email=w.user.email, user_id=w.user.id,
                asset=w.asset.code, balance=w.balance,
                locked_balance=w.locked_balance,
                available_balance=w.available_balance,
                updated_at=w.updated_at,
            )
            for w in items
        ]
        return AdminWalletListResponse(wallets=wallets, meta=meta)
    return await _inner()


# ─── Ledger ───────────────────────────────────────────────────────────────────

@router.get("/ledger", response=AdminLedgerListResponse)
async def list_ledger(
    request,
    page: int = Query(1),
    page_size: int = Query(25),
    search: str = Query(None),
    transaction_type: str = Query(None),
):
    @sync_to_async
    def _inner():
        from wallets.models import Ledger

        qs = Ledger.objects.select_related("user", "wallet_balance", "wallet_balance__asset").all()
        if search:
            qs = qs.filter(user__email__icontains=search)
        if transaction_type:
            qs = qs.filter(transaction_type=transaction_type)

        items, meta = paginate_qs(qs, page, page_size)
        entries = [
            AdminLedgerItem(
                id=e.id, user_email=e.user.email,
                asset=e.wallet_balance.asset.code,
                transaction_type=e.transaction_type, amount=e.amount,
                balance_before=e.balance_before, balance_after=e.balance_after,
                locked_before=e.locked_before, locked_after=e.locked_after,
                reference_id=e.reference_id, reference_model=e.reference_model,
                notes=e.notes, created_at=e.created_at,
            )
            for e in items
        ]
        return AdminLedgerListResponse(entries=entries, meta=meta)
    return await _inner()


# ─── Rates ────────────────────────────────────────────────────────────────────

@router.get("/rates", response=list[AdminRateConfigItem])
async def list_rates(request):
    @sync_to_async
    def _inner():
        from rates.models import RateConfiguration

        configs = RateConfiguration.objects.select_related("asset").all()
        return [
            AdminRateConfigItem(
                asset_code=c.asset.code, asset_name=c.asset.name,
                buy_markup_percent=c.buy_markup_percent,
                sell_markup_percent=c.sell_markup_percent,
                fallback_market_rate=c.fallback_market_rate,
                last_market_rate=c.last_market_rate,
                last_synced_at=c.last_synced_at,
            )
            for c in configs
        ]
    return await _inner()


@router.patch("/rates/{asset_code}", response=MessageSchema)
async def update_rate(request, asset_code: str, payload: AdminRateUpdateSchema):
    @sync_to_async
    def _inner():
        from rates.models import RateConfiguration

        config = RateConfiguration.objects.get(asset__code=asset_code)
        if payload.buy_markup_percent is not None:
            config.buy_markup_percent = payload.buy_markup_percent
        if payload.sell_markup_percent is not None:
            config.sell_markup_percent = payload.sell_markup_percent
        config.save()
        logger.info(f"Admin {request.auth.email} updated rate config for {asset_code}: {payload.dict(exclude_none=True)}")

        try:
            import html
            from notifications.telegram import send_telegram_alert
            _ts = timezone.now().strftime("%Y-%m-%d %H:%M UTC")
            _changes = str(payload.dict(exclude_none=True))
            telegram_msg = (
                f"📈 <b>RATE CONFIG UPDATED</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"👮 Action By: {html.escape(request.auth.email)}\n"
                f"🪙 Asset: {html.escape(asset_code)}\n"
                f"🔧 Changes: {html.escape(_changes)}\n"
                f"⏰ {_ts}"
            )
            send_telegram_alert(telegram_msg)
        except Exception:
            pass

        return MessageSchema(detail=f"Rate config for {asset_code} updated.")
    return await _inner()


# ─── Reserves ─────────────────────────────────────────────────────────────────

@router.get("/reserves", response=AdminReservesResponse)
async def list_reserves(request):
    @sync_to_async
    def _inner():
        from wallets.models import PlatformReserve, ReserveMovement

        reserves = PlatformReserve.objects.select_related("asset").all()
        movements = ReserveMovement.objects.select_related("asset").all()[:50]

        return AdminReservesResponse(
            reserves=[
                AdminReserveItem(asset_code=r.asset.code, balance=r.balance, updated_at=r.updated_at)
                for r in reserves
            ],
            movements=[
                AdminReserveMovementItem(
                    asset_code=m.asset.code, movement_type=m.movement_type,
                    amount=m.amount, notes=m.notes, created_at=m.created_at,
                )
                for m in movements
            ],
        )
    return await _inner()


# ─── Quidax ──────────────────────────────────────────────────────────────────

@router.get("/quidax", response=AdminQuidaxResponse)
async def quidax_overview(
    request,
    page: int = Query(1),
    page_size: int = Query(25),
):
    @sync_to_async
    def _inner():
        from quidax.models import QuidaxDeposit, QuidaxWithdrawal, QuidaxWebhookEvent

        dep_qs = QuidaxDeposit.objects.select_related("user").filter(status=QuidaxDeposit.SUCCESSFUL)
        dep_items, dep_meta = paginate_qs(dep_qs, page, page_size)

        wd_qs = QuidaxWithdrawal.objects.select_related("user").all()
        wd_items, wd_meta = paginate_qs(wd_qs, page, page_size)

        webhooks = QuidaxWebhookEvent.objects.all()[:25]

        return AdminQuidaxResponse(
            deposits=[
                AdminQuidaxDepositItem(
                    id=d.id, user_email=d.user.email, currency=d.currency,
                    amount=d.amount, status=d.status, txid=d.txid, created_at=d.created_at,
                )
                for d in dep_items
            ],
            deposits_meta=dep_meta,
            withdrawals=[
                AdminQuidaxWithdrawalItem(
                    id=w.id, user_email=w.user.email, currency=w.currency,
                    amount=w.amount, status=w.status, reference=w.reference, created_at=w.created_at,
                )
                for w in wd_items
            ],
            withdrawals_meta=wd_meta,
            webhooks=[
                AdminQuidaxWebhookItem(
                    id=e.id, event_type=e.event_type,
                    provider_event_id=e.provider_event_id,
                    processed_at=e.processed_at, created_at=e.created_at,
                )
                for e in webhooks
            ],
        )
    return await _inner()


# ─── Gift Cards ───────────────────────────────────────────────────────────────

def _serialize_gift_card(s) -> AdminGiftCardItem:
    return AdminGiftCardItem(
        id=s.id,
        user_email=s.user.email,
        user_id=s.user_id,
        category=s.category,
        card_currency=s.card_currency,
        declared_value=s.declared_value,
        card_images=s.card_images,
        card_number=s.card_number,
        card_pin=s.card_pin,
        notes=s.notes,
        status=s.status,
        ngn_payout=s.ngn_payout,
        admin_note=s.admin_note,
        reviewed_by_id=s.reviewed_by_id,
        reviewed_at=s.reviewed_at,
        created_at=s.created_at,
        updated_at=s.updated_at,
    )


@router.get("/giftcards", response=AdminGiftCardListResponse)
async def admin_list_gift_cards(
    request,
    page: int = Query(1),
    page_size: int = Query(25),
    status: str = Query(None),
    search: str = Query(None),
):
    """List all gift card submissions (admin only)."""
    @sync_to_async
    def _inner():
        from django.db.models import Q
        from giftcards.models import GiftCardSubmission

        qs = GiftCardSubmission.objects.select_related("user", "reviewed_by").all()
        if status:
            qs = qs.filter(status=status)
        if search:
            qs = qs.filter(user__email__icontains=search)

        items, meta = paginate_qs(qs, page, page_size)
        return AdminGiftCardListResponse(
            submissions=[_serialize_gift_card(s) for s in items],
            meta=meta,
        )
    return await _inner()


@router.get("/giftcards/{submission_id}", response=AdminGiftCardItem)
async def admin_get_gift_card(request, submission_id: str):
    """Get a single gift card submission detail (admin only)."""
    @sync_to_async
    def _inner():
        from giftcards.models import GiftCardSubmission
        s = GiftCardSubmission.objects.select_related("user", "reviewed_by").get(id=submission_id)
        return _serialize_gift_card(s)
    return await _inner()


@router.post("/giftcards/{submission_id}/approve", response=MessageSchema)
async def admin_approve_gift_card(request, submission_id: str, payload: AdminGiftCardApproveSchema):
    """Approve a gift card submission and set the NGN payout (admin only)."""
    @sync_to_async
    def _inner():
        from giftcards.models import GiftCardSubmission
        from giftcards.services import approve_gift_card

        s = GiftCardSubmission.objects.select_related("user").get(id=submission_id)
        approve_gift_card(
            admin_user=request.auth,
            submission=s,
            ngn_payout=payload.ngn_payout,
            admin_note=payload.admin_note or "",
        )
        logger.info(f"Admin {request.auth.email} approved gift card {submission_id}")
        return MessageSchema(detail="Gift card approved and user notified.")
    return await _inner()


@router.post("/giftcards/{submission_id}/reject", response=MessageSchema)
async def admin_reject_gift_card(request, submission_id: str, payload: AdminGiftCardRejectSchema):
    """Reject a gift card submission (admin only)."""
    @sync_to_async
    def _inner():
        from giftcards.models import GiftCardSubmission
        from giftcards.services import reject_gift_card

        s = GiftCardSubmission.objects.select_related("user").get(id=submission_id)
        reject_gift_card(
            admin_user=request.auth,
            submission=s,
            reason=payload.reason,
        )
        logger.info(f"Admin {request.auth.email} rejected gift card {submission_id}")
        return MessageSchema(detail="Gift card rejected and user notified.")
    return await _inner()
