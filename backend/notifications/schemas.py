from datetime import datetime
from typing import Optional
from uuid import UUID

from ninja import Schema


class NotificationItemSchema(Schema):
    id: UUID
    title: str
    message: str
    type: str
    is_read: bool
    reference_id: Optional[UUID] = None
    reference_type: str = ""
    created_at: datetime


class NotificationListResponse(Schema):
    unread_count: int
    notifications: list[NotificationItemSchema]
    meta: "PaginatedMeta"


class PaginatedMeta(Schema):
    total: int
    page: int
    page_size: int
    total_pages: int


class MessageSchema(Schema):
    detail: str
