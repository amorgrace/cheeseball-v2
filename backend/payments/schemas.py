from uuid import UUID

from ninja import Schema
from pydantic import model_validator


class PaymentSetupSchema(Schema):
    transaction_id: UUID
    payment_method: str

    @model_validator(mode="after")
    def validate_method(self):
        if self.payment_method not in {"paystack", "bank_transfer", "ngn_wallet"}:
            raise ValueError("payment_method must be paystack, bank_transfer, or ngn_wallet")
        return self


class BankTransferSubmissionSchema(Schema):
    receipt_reference: str
    receipt_url: str
    receipt_note: str | None = None

    @model_validator(mode="after")
    def validate_receipt(self):
        if not self.receipt_reference.strip():
            raise ValueError("receipt_reference is required")
        if not self.receipt_url.strip():
            raise ValueError("receipt_url is required")
        if not self.receipt_url.startswith(("http://", "https://")):
            raise ValueError("receipt_url must be a valid URL")
        return self


class PaystackWebhookSchema(Schema):
    event: str
    data: dict


class PaymentRecordSchema(Schema):
    id: UUID
    method: str
    status: str
    provider: str
    provider_reference: str
    receipt_reference: str
    receipt_url: str
    receipt_note: str
    provider_payload: dict
    user_confirmed_at: str | None = None
    verified_at: str | None = None
    created_at: str
    updated_at: str


class PaymentInstructionsSchema(Schema):
    bank_name: str
    account_name: str
    account_number: str
    paystack_public_key: str
