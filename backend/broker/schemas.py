from datetime import datetime
from decimal import Decimal

from ninja import Schema
from pydantic import model_validator


class BuyTransactionCreateSchema(Schema):
    quote_id: int
    wallet_address: str | None = None
    network: str | None = None
    payment_method: str

    @model_validator(mode="after")
    def validate_fields(self):
        if self.payment_method not in {"paystack", "bank_transfer", "ngn_wallet"}:
            raise ValueError("payment_method must be paystack, bank_transfer, or ngn_wallet")
        return self


class SellTransactionCreateSchema(Schema):
    quote_id: int
    crypto_source: str = "external_wallet"
    payout_method: str = "ngn_wallet"
    network: str | None = None
    broker_wallet_address: str | None = None

    @model_validator(mode="after")
    def validate_fields(self):
        if self.crypto_source not in {"external_wallet", "cheeseball_wallet"}:
            raise ValueError("crypto_source must be external_wallet or cheeseball_wallet")
        if self.payout_method != "ngn_wallet":
            raise ValueError("payout_method must be ngn_wallet")
        return self



class TransactionActionSchema(Schema):
    note: str | None = None


class RejectTransactionSchema(Schema):
    reason: str


class TransactionSchema(Schema):
    id: str
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
    crypto_usd_price: Decimal
    wallet_address: str
    network: str
    broker_wallet_address: str
    crypto_source: str
    payout_method: str
    bank_name: str
    bank_account_name: str
    bank_account_number: str
    bank_account_type: str
    admin_notes: str
    rejection_reason: str
    reviewed_at: datetime | None = None
    paid_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
