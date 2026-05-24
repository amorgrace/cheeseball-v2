from datetime import datetime
from decimal import Decimal
from uuid import UUID

from ninja import Schema
from pydantic import model_validator


class ConversionPreviewSchema(Schema):
    rate_lock_id: UUID
    from_asset: str
    to_asset: str
    from_amount: Decimal
    to_amount: Decimal
    rate: Decimal
    markup_percent: Decimal
    expires_at: datetime


class ConversionCreateSchema(Schema):
    from_asset: str
    to_asset: str
    from_amount: Decimal

    @model_validator(mode="after")
    def validate_fields(self):
        if self.from_amount <= 0:
            raise ValueError("from_amount must be greater than 0")
        if self.from_asset == self.to_asset:
            raise ValueError("from_asset and to_asset must be different")
        return self


class ConversionExecuteSchema(Schema):
    rate_lock_id: UUID


class ConversionSchema(Schema):
    id: UUID
    from_asset: str
    to_asset: str
    from_amount: Decimal
    to_amount: Decimal
    rate: Decimal
    markup_percent: Decimal
    status: str
    created_at: datetime
    completed_at: datetime | None = None


class WithdrawalCreateSchema(Schema):
    asset: str
    amount: Decimal
    bank_name: str | None = None
    bank_account_name: str | None = None
    bank_account_number: str | None = None
    wallet_address: str | None = None
    network: str | None = None

    @model_validator(mode="after")
    def validate_fields(self):
        if self.amount <= 0:
            raise ValueError("amount must be greater than 0")
        if not self.asset:
            raise ValueError("asset is required")
        return self


class WithdrawalActionSchema(Schema):
    note: str | None = None


class WithdrawalSchema(Schema):
    id: UUID
    asset: str
    amount: Decimal
    status: str
    bank_name: str
    bank_account_name: str
    bank_account_number: str
    wallet_address: str
    network: str
    admin_notes: str
    rejection_reason: str
    created_at: datetime
    completed_at: datetime | None = None
    reviewed_at: datetime | None = None


class WalletBalanceSchema(Schema):
    asset: str
    balance: Decimal
    locked_balance: Decimal
    available_balance: Decimal


class UserWalletSchema(Schema):
    balances: list[WalletBalanceSchema]


class BalanceSummarySchema(Schema):
    total_balance: Decimal
    total_locked: Decimal
    total_available: Decimal
    estimated_portfolio_value: Decimal
    estimated_locked_value: Decimal
    estimated_available_value: Decimal
    ngn_wallet_balance: Decimal
    ngn_wallet_locked_balance: Decimal
    ngn_wallet_available_balance: Decimal
    wallet_count: int


class DepositCreateSchema(Schema):
    asset: str
    expected_amount: Decimal


class DepositResponseSchema(Schema):
    id: UUID
    asset: str
    expected_amount: Decimal
    platform_address: str
    reference_code: str
    network: str | None = None
    memo_supported: bool = False
    created_at: datetime


class DepositDetailSchema(Schema):
    id: UUID
    asset: str
    expected_amount: Decimal
    actual_amount: Decimal | None = None
    platform_address: str
    reference_code: str
    external_reference: str | None = None
    status: str
    created_at: datetime
    completed_at: datetime | None = None


class AdminDepositCompleteSchema(Schema):
    actual_amount: Decimal
    external_reference: str | None = None
