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
        if self.payment_method not in {"paystack", "bank_transfer", "ngn_wallet"}:
            raise ValueError("payment_method must be paystack, bank_transfer, or ngn_wallet")
        if not self.wallet_address.strip():
            raise ValueError("wallet_address is required")
        return self


class SellTransactionCreateSchema(Schema):
    quote_id: int
    beneficiary_id: UUID

    @model_validator(mode="after")
    def validate_fields(self):
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
    bank_account_type: str
    admin_notes: str
    rejection_reason: str
    reviewed_at: str | None = None
    paid_at: str | None = None
    completed_at: str | None = None
    created_at: str
    updated_at: str
