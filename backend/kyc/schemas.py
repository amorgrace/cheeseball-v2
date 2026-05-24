from datetime import datetime
from uuid import UUID

from ninja import Schema
from pydantic import model_validator


class KYCSubmitSchema(Schema):
    id_type: str
    document_url: str

    @model_validator(mode="after")
    def validate_fields(self):
        allowed_types = {"nin", "passport", "drivers_license", "voters_card", "other"}
        if self.id_type not in allowed_types:
            raise ValueError("id_type is invalid")
        if not self.document_url.strip():
            raise ValueError("document_url is required")
        return self


class KYCReviewSchema(Schema):
    note: str | None = None


class KYCRejectSchema(Schema):
    reason: str

    @model_validator(mode="after")
    def validate_fields(self):
        if not self.reason.strip():
            raise ValueError("reason is required")
        return self


class KYCSubmissionSchema(Schema):
    id: UUID
    user_id: UUID
    user_email: str
    id_type: str
    document_url: str
    status: str
    admin_note: str
    reviewed_by_id: UUID | None = None
    reviewed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class KYCStatusSchema(Schema):
    kyc_status: str
    latest_submission: KYCSubmissionSchema | None = None

