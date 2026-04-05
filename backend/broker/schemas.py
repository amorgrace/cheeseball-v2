from decimal import Decimal
from uuid import UUID

from ninja import Schema
from pydantic import model_validator


class BuyTransactionCreateSchema(Schema):
    quote_id: int
    wallet_address: str
    network: str | None = None
    payment_method: str

    @model_validator(mode="after")
    def validate_fields(self):
        if self.payment_method not in {"paystack", "bank_transfer"}:
            raise ValueError("payment_method must be paystack or bank_transfer")
        if not self.wallet_address.strip():
            raise ValueError("wallet_address is required")
        return self


class SellTransactionCreateSchema(Schema):
    quote_id: int
    bank_name: str
    bank_account_name: str
    bank_account_number: str

    @model_validator(mode="after")
    def validate_fields(self):
        if not self.bank_name.strip():
            raise ValueError("bank_name is required")
        if not self.bank_account_name.strip():
            raise ValueError("bank_account_name is required")
        if not self.bank_account_number.strip():
            raise ValueError("bank_account_number is required")
        return self


class TransactionActionSchema(Schema):
    note: str | None = None


class RejectTransactionSchema(Schema):
    reason: str


class TransactionSchema(Schema):
    id: UUID
    transaction_type: str
    asset_code: str
    asset_name: str
    status: str
    payment_method: str | None = None
    naira_amount: Decimal
    crypto_amount: Decimal
    market_rate: Decimal
    markup_percent: Decimal
    final_rate: Decimal
    wallet_address: str
    network: str
    broker_wallet_address: str
    bank_name: str
    bank_account_name: str
    bank_account_number: str
    admin_notes: str
    rejection_reason: str
    reviewed_at: str | None = None
    paid_at: str | None = None
    completed_at: str | None = None
    created_at: str
    updated_at: str
