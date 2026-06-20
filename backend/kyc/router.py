from uuid import UUID

from ninja import Router

from authenticator.auth import JWTAuth

from .schemas import KYCRejectSchema, KYCReviewSchema, KYCStatusSchema, KYCSubmissionSchema, KYCSubmitSchema
from .views import approve, get_my_kyc, list_submissions, reject, submit_submission

router = Router(tags=["KYC"])


@router.post("/submit", response=KYCSubmissionSchema, auth=JWTAuth())
def submit(request, payload: KYCSubmitSchema):
    return submit_submission(request, payload)


@router.get("/me", response=KYCStatusSchema, auth=JWTAuth())
def my_kyc(request):
    return get_my_kyc(request)


@router.get("/admin/submissions", response=list[KYCSubmissionSchema], auth=JWTAuth())
def admin_submissions(request, status: str | None = None):
    return list_submissions(request, status)


@router.post("/admin/submissions/{submission_id}/approve", response=KYCSubmissionSchema, auth=JWTAuth())
def admin_approve(request, submission_id: UUID, payload: KYCReviewSchema):
    return approve(request, submission_id, payload)


@router.post("/admin/submissions/{submission_id}/reject", response=KYCSubmissionSchema, auth=JWTAuth())
def admin_reject(request, submission_id: UUID, payload: KYCRejectSchema):
    return reject(request, submission_id, payload)

