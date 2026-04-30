from uuid import UUID

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from ninja.responses import Response

from .models import KYCSubmission
from .services import approve_submission, reject_submission, submit_kyc


def _serialize_submission(submission: KYCSubmission):
    return {
        "id": submission.id,
        "user_id": submission.user.id,
        "user_email": submission.user.email,
        "id_type": submission.id_type,
        "document_url": submission.document_url,
        "status": submission.status,
        "admin_note": submission.admin_note,
        "reviewed_by_id": submission.reviewed_by_id,
        "reviewed_at": submission.reviewed_at.isoformat() if submission.reviewed_at else None,
        "created_at": submission.created_at.isoformat(),
        "updated_at": submission.updated_at.isoformat(),
    }


def submit_submission(request, payload):
    try:
        submission = submit_kyc(user=request.auth, payload=payload)
        return _serialize_submission(submission)
    except ValidationError as exc:
        return Response({"detail": str(exc)}, status=400)


def get_my_kyc(request):
    latest_submission = KYCSubmission.objects.filter(user=request.auth).order_by("-created_at").first()
    return {
        "kyc_status": request.auth.kyc_status,
        "latest_submission": _serialize_submission(latest_submission) if latest_submission else None,
    }


def list_submissions(request, status: str | None = None):
    from broker.services import ensure_admin

    ensure_admin(request.auth)
    queryset = KYCSubmission.objects.all()
    if status:
        queryset = queryset.filter(status=status)
    return [_serialize_submission(item) for item in queryset.order_by("-created_at")]


def approve(request, submission_id: UUID, payload):
    submission = get_object_or_404(KYCSubmission, id=submission_id)
    try:
        updated = approve_submission(admin_user=request.auth, submission=submission, note=payload.note or "")
        return _serialize_submission(updated)
    except ValidationError as exc:
        return Response({"detail": str(exc)}, status=400)


def reject(request, submission_id: UUID, payload):
    submission = get_object_or_404(KYCSubmission, id=submission_id)
    try:
        updated = reject_submission(admin_user=request.auth, submission=submission, reason=payload.reason)
        return _serialize_submission(updated)
    except ValidationError as exc:
        return Response({"detail": str(exc)}, status=400)

