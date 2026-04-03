from ninja import Schema
from django.core.validators import validate_email
from pydantic import field_validator, model_validator


class RegisterSchema(Schema):
    email: str
    password: str
    confirm_password: str
    referral_code: str | None = None

    @field_validator("email")
    @classmethod
    def validate_email_address(cls, value: str):
        validate_email(value)
        return value

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
        validate_email(value)
        return value


class TokenSchema(Schema):
    access: str
    refresh: str
    message: str | None = None


class RefreshTokenInput(Schema):
    refresh_token: str


class MessageSchema(Schema):
    message: str
