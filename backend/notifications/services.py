import logging
import re
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from .models import Notification

logger = logging.getLogger(__name__)


# KYC state card styles
_KYC_CONFIGS = {
    Notification.KYC_APPROVED: {
        "kyc_status_title": "Identity Verified",
        "kyc_status_subtitle": "You now have full access to all platform features.",
        "kyc_pill_label": "Verification",
        "pill_bg": "#F0FDF4",
        "status_color": "#16A34A",
    },
    Notification.KYC_REJECTED: {
        "kyc_status_title": "Action Required",
        "kyc_status_subtitle": "Your submission could not be verified. Please re-submit.",
        "kyc_pill_label": "Rejected",
        "pill_bg": "#FEF2F2",
        "status_color": "#DC2626",
    },
    "KYC_SUBMITTED": {
        "kyc_status_title": "Under Review",
        "kyc_status_subtitle": "We are reviewing your documents. This usually takes 24–48 hours.",
        "kyc_pill_label": "Submitted",
        "pill_bg": "#FFFBEB",
        "status_color": "#D97706",
    },
    "KYC_PENDING": {
        "kyc_status_title": "Verification Required",
        "kyc_status_subtitle": "Complete KYC to unlock withdrawals, higher limits, and more.",
        "kyc_pill_label": "Action Required",
        "pill_bg": "#EEF3FF",
        "status_color": "#1A6FFF",
    },
}


def _extract_amount(message: str, notification_type: str) -> str:
    """Helper to extract currency amounts like '$250.00 USD', '0.05 BTC', or '₦1,000.00' from message strings."""
    pattern = r'(?:[₦$]\s*\d+(?:[.,]\d+)*)|(?:\d+(?:[.,]\d+)*\s*[A-Z]{3,4})'
    match = re.search(pattern, message)
    if match:
        val = match.group(0)
        # Prefix with plus or minus depending on type
        if notification_type in (Notification.DEPOSIT_RECEIVED, Notification.CRYPTO_RECEIVED, Notification.REFERRAL_REWARD):
            return f"+{val}"
        elif notification_type in (Notification.WITHDRAWAL_APPROVED, Notification.CRYPTO_SENT):
            return f"-{val}"
        return val
    return None


def _extract_details(message: str) -> dict:
    """Helper to pull basic fields like Recipient, Sender, or Rejection Reason out of standard strings."""
    details = {}
    if "Reason:" in message:
        parts = message.split("Reason:")
        if len(parts) > 1:
            details["Reason"] = parts[1].split(".")[0].strip()

    to_match = re.search(r'\bto\s+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}|0x[a-fA-F0-9]{40}|[a-zA-Z0-9]{26,35})', message)
    if to_match:
        details["Recipient"] = to_match.group(1)

    from_match = re.search(r'\bfrom\s+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', message)
    if from_match:
        details["Sender"] = from_match.group(1)

    return details if details else None


def _send_notification_email(user, title: str, message: str, notification_type: str, extra_context: dict = None):
    """Safely send an email notification for major business activities."""
    if not getattr(user, "email", None):
        return

    category_map = {
        Notification.TRANSACTION_COMPLETED: "Trade Activity",
        Notification.TRANSACTION_FAILED: "Trade Activity",
        Notification.TRANSACTION_REJECTED: "Trade Activity",
        Notification.DEPOSIT_RECEIVED: "Deposit Alert",
        Notification.WITHDRAWAL_APPROVED: "Withdrawal Alert",
        Notification.WITHDRAWAL_REJECTED: "Withdrawal Alert",
        Notification.KYC_APPROVED: "Verification Status",
        Notification.KYC_REJECTED: "Verification Status",
        Notification.CRYPTO_SENT: "Transfer Alert",
        Notification.CRYPTO_RECEIVED: "Transfer Alert",
        Notification.REFERRAL_REWARD: "Reward Alert",
    }

    category = category_map.get(notification_type, "Account Activity")
    user_name = getattr(user, "full_name", None) or getattr(user, "first_name", None) or user.email.split("@")[0]

    is_kyc = notification_type in _KYC_CONFIGS or notification_type in (Notification.KYC_APPROVED, Notification.KYC_REJECTED)
    template_name = "emails/activity_notification.html" # Fallback (should be overridden by extra_context)

    # Default styled status pill and color tones for activity notifications
    style_defaults = {
        Notification.TRANSACTION_COMPLETED: {"status_color": "#16A34A", "pill_bg": "#F0FDF4", "status_badge": "Filled"},
        Notification.TRANSACTION_FAILED: {"status_color": "#DC2626", "pill_bg": "#FEF2F2", "status_badge": "Failed"},
        Notification.TRANSACTION_REJECTED: {"status_color": "#DC2626", "pill_bg": "#FEF2F2", "status_badge": "Rejected"},
        Notification.DEPOSIT_RECEIVED: {"status_color": "#16A34A", "pill_bg": "#F0FDF4", "status_badge": "Completed"},
        Notification.WITHDRAWAL_APPROVED: {"status_color": "#16A34A", "pill_bg": "#F0FDF4", "status_badge": "Sent"},
        Notification.WITHDRAWAL_REJECTED: {"status_color": "#DC2626", "pill_bg": "#FEF2F2", "status_badge": "Declined"},
        Notification.CRYPTO_SENT: {"status_color": "#1A6FFF", "pill_bg": "#EEF3FF", "status_badge": "Sent"},
        Notification.CRYPTO_RECEIVED: {"status_color": "#16A34A", "pill_bg": "#F0FDF4", "status_badge": "Received"},
        Notification.REFERRAL_REWARD: {"status_color": "#16A34A", "pill_bg": "#F0FDF4", "status_badge": "Earned"},
    }

    # Default action buttons for transactional emails
    cta_defaults = {
        Notification.TRANSACTION_COMPLETED: {"cta_text": "View Wallet", "cta_url": "https://cheeseballapp.com/dashboard/wallets"},
        Notification.TRANSACTION_FAILED: {"cta_text": "Go to Dashboard", "cta_url": "https://cheeseballapp.com/dashboard"},
        Notification.TRANSACTION_REJECTED: {"cta_text": "Go to Dashboard", "cta_url": "https://cheeseballapp.com/dashboard"},
        Notification.DEPOSIT_RECEIVED: {"cta_text": "View Wallet Balance", "cta_url": "https://cheeseballapp.com/dashboard/wallets"},
        Notification.WITHDRAWAL_APPROVED: {"cta_text": "Check History", "cta_url": "https://cheeseballapp.com/dashboard/history"},
        Notification.WITHDRAWAL_REJECTED: {"cta_text": "Go to Dashboard", "cta_url": "https://cheeseballapp.com/dashboard"},
        Notification.CRYPTO_SENT: {"cta_text": "Track Transaction", "cta_url": "https://cheeseballapp.com/dashboard/history"},
        Notification.CRYPTO_RECEIVED: {"cta_text": "View Wallet Balance", "cta_url": "https://cheeseballapp.com/dashboard/wallets"},
        Notification.REFERRAL_REWARD: {"cta_text": "View Balance", "cta_url": "https://cheeseballapp.com/dashboard/wallets"},
    }

    context = {
        "user_name": user_name,
        "category": category,
        "notification_title": title,
        "notification_message": message,
        "headline": title,
        "preheader": message[:150],
        "help_text": "Need help? Contact support@cheeseballapp.com",
    }

    # Apply defaults if applicable
    if notification_type in style_defaults:
        context.update(style_defaults[notification_type])
    if notification_type in cta_defaults:
        context.update(cta_defaults[notification_type])

    # Extract big amount if not explicitly passed
    extracted_amt = _extract_amount(message, notification_type)
    if extracted_amt:
        context["big_amount"] = extracted_amt

    # Extract details if not explicitly passed
    extracted_details = _extract_details(message)
    if extracted_details:
        context["details"] = extracted_details

    # Merge KYC-specific card styling if applicable
    kyc_cfg = _KYC_CONFIGS.get(notification_type)
    if kyc_cfg:
        context.update(kyc_cfg)

    # Allow callers to pass extra template context (e.g. details dict, cta_text)
    if extra_context:
        context.update(extra_context)

    text_template_name = "emails/activity_notification.txt"
    if extra_context and "template_name" in extra_context:
        template_name = extra_context["template_name"]
    if extra_context and "text_template_name" in extra_context:
        text_template_name = extra_context["text_template_name"]

    try:
        html_body = render_to_string(template_name, context)
        text_body = render_to_string(text_template_name, context)

        msg = EmailMultiAlternatives(
            subject=f"[CheeseBall] {title}",
            body=text_body,
            to=[user.email],
        )
        msg.attach_alternative(html_body, "text/html")
        msg.send(fail_silently=True)
    except Exception:
        logger.exception("Failed to dispatch email notification to %s", user.email)


def send_kyc_prompt_email(user):
    """
    Send a 'Complete Your KYC' email right after a user's account is activated via OTP.
    This is NOT an in-app notification — just an email nudge.
    """
    user_name = getattr(user, "full_name", None) or getattr(user, "first_name", None) or user.email.split("@")[0]
    context = {
        "user_name": user_name,
        "headline": "Complete Your Verification",
        "category": "Verification Status",
        "notification_message": (
            "Welcome to CheeseBall! Your account is now active. "
            "To unlock withdrawals, higher trading limits, and full platform access, "
            "please complete your identity verification."
        ),
        "kyc_status_title": "Verification Required",
        "kyc_status_subtitle": "Takes less than 5 minutes.",
        "kyc_pill_label": "Action Required",
        "pill_bg": "#EEF3FF",
        "status_color": "#1A6FFF",
        "cta_text": "Verify My Identity",
        "cta_url": "https://cheeseballapp.com/dashboard/kyc",
        "help_text": "Need help? Contact support@cheeseballapp.com",
    }
    try:
        html_body = render_to_string("emails/kyc_prompt.html", context)
        text_body = render_to_string("emails/kyc_prompt.txt", context)
        msg = EmailMultiAlternatives(
            subject="[CheeseBall] Complete Your Identity Verification",
            body=text_body,
            to=[user.email],
        )
        msg.attach_alternative(html_body, "text/html")
        msg.send(fail_silently=True)
    except Exception:
        logger.exception("Failed to send KYC prompt email to %s", user.email)


def notify(user, *, title, message, notification_type=Notification.GENERAL, reference_id=None, reference_type="", extra_context: dict = None):
    """
    Create an in-app notification for a user and dispatch an email alert.
    Pass extra_context to supply template variables like details, cta_text, big_amount, banner_gradient.
    """
    notification = None
    try:
        notification = Notification.objects.create(
            user=user,
            title=title,
            message=message,
            type=notification_type,
            reference_id=reference_id,
            reference_type=reference_type,
        )
    except Exception:
        logger.exception("Failed to create notification for user %s", getattr(user, "email", user))

    # Trigger email dispatch
    _send_notification_email(user, title, message, notification_type, extra_context=extra_context)

    return notification
