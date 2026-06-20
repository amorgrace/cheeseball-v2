import logging

from .models import Notification

logger = logging.getLogger(__name__)


def notify(user, *, title, message, notification_type=Notification.GENERAL, reference_id=None, reference_type=""):
    """
    Create an in-app notification for a user.

    Args:
        user: The user to notify.
        title: Short notification title (e.g. "Transaction Completed").
        message: Detailed message body.
        notification_type: One of Notification.TYPE_CHOICES.
        reference_id: UUID of the related object (Transaction, KYC, Withdrawal, etc.).
        reference_type: Model name string for deep-linking (e.g. "Transaction").
    """
    try:
        return Notification.objects.create(
            user=user,
            title=title,
            message=message,
            type=notification_type,
            reference_id=reference_id,
            reference_type=reference_type,
        )
    except Exception:
        logger.exception("Failed to create notification for user %s", user.email)
        return None
