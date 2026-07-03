from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from ninja import Schema
from pydantic import model_validator


# ── User-facing submission schema ─────────────────────────────────────────────

ALLOWED_CATEGORIES = {
    "amazon", "itunes", "google_play", "steam", "netflix",
    "xbox", "playstation", "ebay", "walmart", "other",
}
ALLOWED_CURRENCIES = {"usd", "gbp", "eur", "cad", "aud"}

CLOUDINARY_PREFIXES = (
    "https://res.cloudinary.com/",
    "http://res.cloudinary.com/",
)


class GiftCardSubmitSchema(Schema):
    category: str
    card_currency: str
    declared_value: Decimal
    card_images: str          # comma-separated Cloudinary URLs
    card_number: Optional[str] = ""
    card_pin: Optional[str] = ""
    notes: Optional[str] = ""

    @model_validator(mode="after")
    def validate_fields(self):
        if self.category not in ALLOWED_CATEGORIES:
            raise ValueError(f"Invalid category. Must be one of: {', '.join(sorted(ALLOWED_CATEGORIES))}")
        if self.card_currency not in ALLOWED_CURRENCIES:
            raise ValueError(f"Invalid currency. Must be one of: {', '.join(sorted(ALLOWED_CURRENCIES))}")
        if self.declared_value <= 0:
            raise ValueError("declared_value must be greater than zero.")
        # Validate that at least one Cloudinary URL is provided
        urls = [u.strip() for u in self.card_images.split(",") if u.strip()]
        if not urls:
            raise ValueError("At least one card image URL is required.")
        for url in urls:
            if not any(url.startswith(p) for p in CLOUDINARY_PREFIXES):
                raise ValueError(f"All card_images must be Cloudinary URLs. Got: {url}")
        return self


# ── Response schemas ──────────────────────────────────────────────────────────

class GiftCardSubmissionSchema(Schema):
    id: UUID
    user_id: UUID
    user_email: str
    category: str
    card_currency: str
    declared_value: Decimal
    card_images: str
    card_number: str
    card_pin: str
    notes: str
    status: str
    ngn_payout: Optional[Decimal] = None
    admin_note: str
    reviewed_by_id: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class GiftCardListResponse(Schema):
    submissions: List[GiftCardSubmissionSchema]
    total: int
