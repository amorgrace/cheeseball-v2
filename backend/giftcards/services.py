import html as _html
import logging

from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import GiftCardSubmission

logger = logging.getLogger(__name__)


def submit_gift_card(*, user, payload) -> GiftCardSubmission:
    """
    Create a new GiftCardSubmission for the given user.
    Raises ValidationError if the user already has a pending submission
    for the same category (prevent spam).
    """
    existing_pending = GiftCardSubmission.objects.filter(
        user=user,
        category=payload.category,
        status=GiftCardSubmission.PENDING,
    ).exists()
    if existing_pending:
        raise ValidationError(
            "You already have a pending submission for this gift card category. "
            "Please wait for it to be reviewed before submitting another."
        )

    submission = GiftCardSubmission.objects.create(
        user=user,
        category=payload.category,
        card_currency=payload.card_currency,
        declared_value=payload.declared_value,
        card_images=payload.card_images,
        card_number=payload.card_number or "",
        card_pin=payload.card_pin or "",
        notes=payload.notes or "",
        status=GiftCardSubmission.PENDING,
    )

    # ── Telegram alert to admin ───────────────────────────────────────────
    try:
        from django.utils import timezone as _tz
        from notifications.telegram import send_telegram_alert
        _ts = _tz.now().strftime("%Y-%m-%d %H:%M UTC")
        msg = (
            f"🎁 <b>NEW GIFT CARD SUBMISSION</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 User: {_html.escape(user.email)}\n"
            f"🏷️ Category: {_html.escape(submission.get_category_display())}\n"
            f"💱 Currency: {submission.card_currency.upper()}\n"
            f"💰 Value: {submission.card_currency.upper()} {submission.declared_value:,.2f}\n"
            f"📌 Status: Awaiting Review\n"
            f"⏰ {_ts}"
        )
        send_telegram_alert(msg)
    except Exception:
        logger.exception("Failed to send Telegram alert for gift card submission %s", submission.id)

    return submission


def approve_gift_card(*, admin_user, submission: GiftCardSubmission, ngn_payout, admin_note: str = "") -> GiftCardSubmission:
    """
    Approve a pending gift card submission, set the NGN payout, and notify the user.
    """
    if submission.status != GiftCardSubmission.PENDING:
        raise ValidationError("Only pending gift card submissions can be approved.")

    submission.status = GiftCardSubmission.APPROVED
    submission.ngn_payout = ngn_payout
    submission.admin_note = (admin_note or "").strip()
    submission.reviewed_by = admin_user
    submission.reviewed_at = timezone.now()
    submission.save(update_fields=["status", "ngn_payout", "admin_note", "reviewed_by", "reviewed_at", "updated_at"])

    # ── In-app + email notification to user ───────────────────────────────────
    try:
        from notifications.models import Notification
        from notifications.services import notify
        notify(
            submission.user,
            title="Gift Card Approved",
            message=(
                f"Your {submission.get_category_display()} gift card "
                f"({submission.card_currency.upper()} {submission.declared_value:,.2f}) "
                f"has been approved. You will receive ₦{ngn_payout:,.2f} NGN."
            ),
            notification_type=Notification.GENERAL,
            reference_id=str(submission.id),
            reference_type="GiftCardSubmission",
        )
    except Exception:
        logger.exception("Failed to send approval notification for gift card %s", submission.id)

    # ── Telegram alert to admin ───────────────────────────────────────────
    try:
        from django.utils import timezone as _tz
        from notifications.telegram import send_telegram_alert
        _ts = _tz.now().strftime("%Y-%m-%d %H:%M UTC")
        msg = (
            f"✅ <b>GIFT CARD APPROVED</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 User: {_html.escape(submission.user.email)}\n"
            f"🏷️ Category: {_html.escape(submission.get_category_display())}\n"
            f"💰 Declared Value: {submission.card_currency.upper()} {submission.declared_value:,.2f}\n"
            f"💵 NGN Payout: ₦{ngn_payout:,.2f}\n"
            f"👮 Action By: {_html.escape(admin_user.email)}\n"
            f"⏰ {_ts}"
        )
        send_telegram_alert(msg)
    except Exception:
        logger.exception("Failed to send Telegram alert for gift card approval %s", submission.id)

    return submission


def reject_gift_card(*, admin_user, submission: GiftCardSubmission, reason: str) -> GiftCardSubmission:
    """
    Reject a pending gift card submission and notify the user with the reason.
    """
    if submission.status != GiftCardSubmission.PENDING:
        raise ValidationError("Only pending gift card submissions can be rejected.")
    if not reason.strip():
        raise ValidationError("A rejection reason is required.")

    submission.status = GiftCardSubmission.REJECTED
    submission.admin_note = reason.strip()
    submission.reviewed_by = admin_user
    submission.reviewed_at = timezone.now()
    submission.save(update_fields=["status", "admin_note", "reviewed_by", "reviewed_at", "updated_at"])

    # ── In-app + email notification to user ───────────────────────────────────
    try:
        from notifications.models import Notification
        from notifications.services import notify
        notify(
            submission.user,
            title="Gift Card Rejected",
            message=(
                f"Your {submission.get_category_display()} gift card submission was rejected. "
                f"Reason: {reason}"
            ),
            notification_type=Notification.GENERAL,
            reference_id=str(submission.id),
            reference_type="GiftCardSubmission",
        )
    except Exception:
        logger.exception("Failed to send rejection notification for gift card %s", submission.id)

    # ── Telegram alert to admin ───────────────────────────────────────────
    try:
        from django.utils import timezone as _tz
        from notifications.telegram import send_telegram_alert
        _ts = _tz.now().strftime("%Y-%m-%d %H:%M UTC")
        msg = (
            f"❌ <b>GIFT CARD REJECTED</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 User: {_html.escape(submission.user.email)}\n"
            f"🏷️ Category: {_html.escape(submission.get_category_display())}\n"
            f"💰 Declared Value: {submission.card_currency.upper()} {submission.declared_value:,.2f}\n"
            f"📝 Reason: {_html.escape(reason)}\n"
            f"👮 Action By: {_html.escape(admin_user.email)}\n"
            f"⏰ {_ts}"
        )
        send_telegram_alert(msg)
    except Exception:
        logger.exception("Failed to send Telegram alert for gift card rejection %s", submission.id)

    return submission
