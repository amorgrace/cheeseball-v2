from decimal import Decimal
from typing import Optional
from uuid import UUID

from asgiref.sync import sync_to_async
from ninja import Router, Query

from authenticator.auth import JWTAuth

from .models import GiftCardSubmission
from .schemas import GiftCardListResponse, GiftCardSubmissionSchema, GiftCardSubmitSchema

router = Router(tags=["Gift Cards"], auth=JWTAuth())


def _serialize(submission: GiftCardSubmission) -> GiftCardSubmissionSchema:
    return GiftCardSubmissionSchema(
        id=submission.id,
        user_id=submission.user_id,
        user_email=submission.user.email,
        category=submission.category,
        card_currency=submission.card_currency,
        declared_value=submission.declared_value,
        card_images=submission.card_images,
        card_number=submission.card_number,
        card_pin=submission.card_pin,
        notes=submission.notes,
        status=submission.status,
        ngn_payout=submission.ngn_payout,
        admin_note=submission.admin_note,
        reviewed_by_id=submission.reviewed_by_id,
        reviewed_at=submission.reviewed_at,
        created_at=submission.created_at,
        updated_at=submission.updated_at,
    )


@router.post("/submit", response=GiftCardSubmissionSchema)
async def submit_gift_card(request, payload: GiftCardSubmitSchema):
    """Submit a new gift card for review."""
    @sync_to_async
    def _inner():
        from .services import submit_gift_card as _submit
        submission = _submit(user=request.auth, payload=payload)
        return _serialize(submission)
    return await _inner()


@router.get("/my", response=GiftCardListResponse)
async def my_gift_cards(
    request,
    status: Optional[str] = Query(None),
    page: int = Query(1),
    page_size: int = Query(25),
):
    """List the authenticated user's own gift card submissions."""
    @sync_to_async
    def _inner():
        qs = GiftCardSubmission.objects.select_related("user", "reviewed_by").filter(user=request.auth)
        if status:
            qs = qs.filter(status=status)
        page_num = max(1, page)
        ps = min(max(1, page_size), 100)
        total = qs.count()
        offset = (page_num - 1) * ps
        items = list(qs[offset: offset + ps])
        return GiftCardListResponse(
            submissions=[_serialize(s) for s in items],
            total=total,
        )
    return await _inner()


@router.get("/{submission_id}", response=GiftCardSubmissionSchema)
async def get_gift_card(request, submission_id: UUID):
    """Get a single gift card submission (must belong to the authenticated user)."""
    @sync_to_async
    def _inner():
        submission = GiftCardSubmission.objects.select_related("user", "reviewed_by").get(
            id=submission_id, user=request.auth
        )
        return _serialize(submission)
    return await _inner()
