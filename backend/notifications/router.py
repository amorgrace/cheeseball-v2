import math

from asgiref.sync import sync_to_async
from ninja import Router, Query

from authenticator.auth import JWTAuth

from .models import Notification
from .schemas import (
    MessageSchema,
    NotificationItemSchema,
    NotificationListResponse,
    PaginatedMeta,
)

router = Router(tags=["Notifications"], auth=JWTAuth())


@router.get("", response=NotificationListResponse)
async def list_notifications(
    request,
    page: int = Query(1),
    page_size: int = Query(25),
    unread_only: bool = Query(False),
):
    """List the authenticated user's notifications (newest first)."""

    @sync_to_async
    def _inner():
        qs = Notification.objects.filter(user=request.auth)
        unread_count = qs.filter(is_read=False).count()

        if unread_only:
            qs = qs.filter(is_read=False)

        page_num = max(1, page)
        ps = min(max(1, page_size), 100)
        total = qs.count()
        total_pages = max(1, math.ceil(total / ps))
        offset = (page_num - 1) * ps
        items = list(qs[offset : offset + ps])

        notifications = [
            NotificationItemSchema(
                id=n.id,
                title=n.title,
                message=n.message,
                type=n.type,
                is_read=n.is_read,
                reference_id=n.reference_id,
                reference_type=n.reference_type,
                created_at=n.created_at,
            )
            for n in items
        ]

        return NotificationListResponse(
            unread_count=unread_count,
            notifications=notifications,
            meta=PaginatedMeta(
                total=total, page=page_num, page_size=ps, total_pages=total_pages
            ),
        )

    return await _inner()


@router.post("/{notification_id}/read", response=MessageSchema)
async def mark_read(request, notification_id: str):
    """Mark a single notification as read."""

    @sync_to_async
    def _inner():
        updated = Notification.objects.filter(
            id=notification_id, user=request.auth
        ).update(is_read=True)
        if not updated:
            return MessageSchema(detail="Notification not found.")
        return MessageSchema(detail="Notification marked as read.")

    return await _inner()


@router.post("/read-all", response=MessageSchema)
async def mark_all_read(request):
    """Mark all of the user's unread notifications as read."""

    @sync_to_async
    def _inner():
        count = Notification.objects.filter(user=request.auth, is_read=False).update(
            is_read=True
        )
        return MessageSchema(detail=f"{count} notifications marked as read.")

    return await _inner()
