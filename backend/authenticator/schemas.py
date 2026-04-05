from uuid import UUID

from django.core.validators import validate_email
from ninja import Schema
from pydantic import field_validator, model_validator


def normalize_email_value(value: str) -> str:
    normalized = value.strip().lower()
    validate_email(normalized)
    return normalized


class RegisterSchema(Schema):
    email: str
    password: str
    confirm_password: str
    referral_code: str | None = None

    @field_validator("email")
    @classmethod
    def validate_email_address(cls, value: str):
        return normalize_email_value(value)

    @model_validator(mode="after")
    def passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class LoginSchema(Schema):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email_address(cls, value: str):
        return normalize_email_value(value)


class TokenSchema(Schema):
    access: str
    refresh: str
    message: str | None = None


class VerificationChallengeSchema(Schema):
    message: str
    verification_token: str
    verification_token_expires_at: str
    resend_available_at: str


class PasswordResetChallengeSchema(Schema):
    message: str
    reset_token: str
    reset_token_expires_at: str
    resend_available_at: str


class RefreshTokenInput(Schema):
    refresh_token: str


class MessageSchema(Schema):
    message: str


class VerifyTokenSchema(Schema):
    email: str
    token: str

    @field_validator("email")
    @classmethod
    def validate_email_address(cls, value: str):
        return normalize_email_value(value)

    @field_validator("token")
    @classmethod
    def validate_token(cls, value: str):
        if not value.isdigit() or len(value) != 6:
            raise ValueError("Token must be a 6-digit code")
        return value


class ResendTokenSchema(Schema):
    email: str

    @field_validator("email")
    @classmethod
    def validate_email_address(cls, value: str):
        return normalize_email_value(value)


class PasswordResetRequestSchema(Schema):
    email: str

    @field_validator("email")
    @classmethod
    def validate_email_address(cls, value: str):
        return normalize_email_value(value)


class PasswordResetConfirmSchema(Schema):
    email: str
    token: str
    password: str
    confirm_password: str

    @field_validator("email")
    @classmethod
    def validate_email_address(cls, value: str):
        return normalize_email_value(value)

    @field_validator("token")
    @classmethod
    def validate_token(cls, value: str):
        if not value.isdigit() or len(value) != 6:
            raise ValueError("Token must be a 6-digit code")
        return value

    @model_validator(mode="after")
    def passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class UserMeSchema(Schema):
    id: UUID
    email: str
    phone_number: str | None = None
    referral_code: str | None = None
    first_name: str
    last_name: str
    is_staff: bool
    verified_at: str | None = None


class UpdateMeSchema(Schema):
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None
