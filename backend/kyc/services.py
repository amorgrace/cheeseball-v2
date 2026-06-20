from django.core.exceptions import ValidationError
from django.utils import timezone

from broker.services import ensure_admin

from .models import KYCSubmission


def _is_cloudinary_url(url: str) -> bool:
    value = (url or "").strip().lower()
    return value.startswith("https://res.cloudinary.com/") or value.startswith("http://res.cloudinary.com/")


def submit_kyc(*, user, payload):
    document_url = payload.document_url.strip()

    if not _is_cloudinary_url(document_url):
        raise ValidationError("document_url must be a Cloudinary URL")

    latest_submission = KYCSubmission.objects.filter(user=user).order_by("-created_at").first()
    if latest_submission and latest_submission.status != KYCSubmission.REJECTED:
        raise ValidationError("You can only submit KYC again after rejection")

    submission = KYCSubmission.objects.create(
        user=user,
        id_type=payload.id_type,
        document_url=document_url,
        status=KYCSubmission.SUBMITTED,
    )
    user.kyc_status = user.KYC_SUBMITTED
    user.save(update_fields=["kyc_status"])
    return submission


def approve_submission(*, admin_user, submission: KYCSubmission, note: str = ""):
    ensure_admin(admin_user)
    if submission.status != KYCSubmission.SUBMITTED:
        raise ValidationError("Only submitted KYC can be approved")
    submission.status = KYCSubmission.VERIFIED
    submission.admin_note = (note or "").strip()
    submission.reviewed_by = admin_user
    submission.reviewed_at = timezone.now()
    submission.save(update_fields=["status", "admin_note", "reviewed_by", "reviewed_at", "updated_at"])
    submission.user.kyc_status = submission.user.KYC_VERIFIED
    submission.user.save(update_fields=["kyc_status"])
    return submission


def reject_submission(*, admin_user, submission: KYCSubmission, reason: str):
    ensure_admin(admin_user)
    if submission.status != KYCSubmission.SUBMITTED:
        raise ValidationError("Only submitted KYC can be rejected")
    submission.status = KYCSubmission.REJECTED
    submission.admin_note = reason.strip()
    submission.reviewed_by = admin_user
    submission.reviewed_at = timezone.now()
    submission.save(update_fields=["status", "admin_note", "reviewed_by", "reviewed_at", "updated_at"])
    submission.user.kyc_status = submission.user.KYC_REJECTED
    submission.user.save(update_fields=["kyc_status"])
    return submission

