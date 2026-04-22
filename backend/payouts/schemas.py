from uuid import UUID

from ninja import Schema
from pydantic import model_validator


class BeneficiaryBankAccountCreateSchema(Schema):
    account_name: str
    bank_name: str
    account_number: str
    account_type: str

    @model_validator(mode="after")
    def validate_fields(self):
        if not self.account_name.strip():
            raise ValueError("account_name is required")
        if not self.bank_name.strip():
            raise ValueError("bank_name is required")
        if not self.account_number.strip():
            raise ValueError("account_number is required")
        if self.account_type not in {"savings", "checking"}:
            raise ValueError("account_type must be savings or checking")
        return self


class BeneficiaryBankAccountSchema(Schema):
    id: UUID
    account_name: str
    bank_name: str
    account_number: str
    account_type: str
    created_at: str
    updated_at: str

