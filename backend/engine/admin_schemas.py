from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from ninja import Schema


# ─── Pagination ───────────────────────────────────────────────────────────────

class PaginatedMeta(Schema):
    total: int
    page: int
    page_size: int
    total_pages: int


# ─── Dashboard Stats ─────────────────────────────────────────────────────────

class DashboardStatsSchema(Schema):
    total_users: int
    verified_users: int
    pending_kyc: int
    total_transactions: int
    pending_transactions: int
    pending_withdrawals: int
    total_volume_ngn: Decimal
    total_volume_24h_ngn: Decimal


# ─── Users ────────────────────────────────────────────────────────────────────

class AdminUserListItem(Schema):
    id: UUID
    email: str
    first_name: str
    last_name: str
    phone_number: Optional[str] = None
    referral_code: str
    kyc_status: str
    is_active: bool
    is_staff: bool
    date_joined: datetime
    last_login: Optional[datetime] = None


class AdminUserListResponse(Schema):
    users: List[AdminUserListItem]
    meta: PaginatedMeta


class AdminUserDetailSchema(Schema):
    id: UUID
    email: str
    first_name: str
    last_name: str
    phone_number: Optional[str] = None
    referral_code: str
    referred_by_email: Optional[str] = None
    referral_count: int = 0
    kyc_status: str
    is_active: bool
    is_staff: bool
    is_superuser: bool
    verified_at: Optional[datetime] = None
    date_joined: datetime
    last_login: Optional[datetime] = None


class AdminUserUpdateSchema(Schema):
    is_active: Optional[bool] = None
    kyc_status: Optional[str] = None


# ─── Transactions ─────────────────────────────────────────────────────────────

class AdminTransactionItem(Schema):
    id: UUID
    user_email: str
    transaction_type: str
    asset: str
    status: str
    payment_method: Optional[str] = None
    naira_amount: Decimal
    crypto_amount: Decimal
    final_rate: Decimal
    created_at: datetime


class AdminTransactionListResponse(Schema):
    transactions: List[AdminTransactionItem]
    meta: PaginatedMeta


class AdminTransactionDetailSchema(Schema):
    id: UUID
    user_email: str
    user_id: UUID
    transaction_type: str
    asset: str
    status: str
    payment_method: Optional[str] = None
    crypto_source: str
    payout_method: str
    naira_amount: Decimal
    crypto_amount: Decimal
    market_rate: Decimal
    markup_percent: Decimal
    final_rate: Decimal
    crypto_usd_price: Decimal
    wallet_address: str
    network: str
    broker_wallet_address: str
    bank_name: str
    bank_account_name: str
    bank_account_number: str
    admin_notes: str
    rejection_reason: str
    reviewed_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class AdminTransactionActionSchema(Schema):
    admin_notes: Optional[str] = None


class AdminTransactionRejectSchema(Schema):
    rejection_reason: str
    admin_notes: Optional[str] = None


# ─── KYC ──────────────────────────────────────────────────────────────────────

class AdminKYCItem(Schema):
    id: UUID
    user_email: str
    user_id: UUID
    id_type: str
    document_url: str
    status: str
    admin_note: str
    reviewed_at: Optional[datetime] = None
    created_at: datetime


class AdminKYCListResponse(Schema):
    submissions: List[AdminKYCItem]
    meta: PaginatedMeta


class AdminKYCReviewSchema(Schema):
    action: str  # "approve" or "reject"
    admin_note: Optional[str] = None


# ─── Withdrawals ──────────────────────────────────────────────────────────────

class AdminWithdrawalItem(Schema):
    id: UUID
    user_email: str
    user_id: UUID
    asset: str
    amount: Decimal
    status: str
    bank_name: str
    bank_account_name: str
    bank_account_number: str
    wallet_address: str
    network: str
    created_at: datetime


class AdminWithdrawalListResponse(Schema):
    withdrawals: List[AdminWithdrawalItem]
    meta: PaginatedMeta


class AdminWithdrawalActionSchema(Schema):
    admin_notes: Optional[str] = None


class AdminWithdrawalRejectSchema(Schema):
    rejection_reason: str
    admin_notes: Optional[str] = None


# ─── Wallets ──────────────────────────────────────────────────────────────────

class AdminWalletItem(Schema):
    id: UUID
    user_email: str
    user_id: UUID
    asset: str
    balance: Decimal
    locked_balance: Decimal
    available_balance: Decimal
    updated_at: datetime


class AdminWalletListResponse(Schema):
    wallets: List[AdminWalletItem]
    meta: PaginatedMeta


# ─── Ledger ───────────────────────────────────────────────────────────────────

class AdminLedgerItem(Schema):
    id: UUID
    user_email: str
    asset: str
    transaction_type: str
    amount: Decimal
    balance_before: Decimal
    balance_after: Decimal
    locked_before: Decimal
    locked_after: Decimal
    reference_id: Optional[UUID] = None
    reference_model: str
    notes: str
    created_at: datetime


class AdminLedgerListResponse(Schema):
    entries: List[AdminLedgerItem]
    meta: PaginatedMeta


# ─── Rates ────────────────────────────────────────────────────────────────────

class AdminRateConfigItem(Schema):
    asset_code: str
    asset_name: str
    buy_markup_percent: Decimal
    sell_markup_percent: Decimal
    fallback_market_rate: Decimal
    last_market_rate: Optional[Decimal] = None
    last_synced_at: Optional[datetime] = None


class AdminRateUpdateSchema(Schema):
    buy_markup_percent: Optional[Decimal] = None
    sell_markup_percent: Optional[Decimal] = None


# ─── Reserves ─────────────────────────────────────────────────────────────────

class AdminReserveItem(Schema):
    asset_code: str
    balance: Decimal
    updated_at: datetime


class AdminReserveMovementItem(Schema):
    asset_code: str
    movement_type: str
    amount: Decimal
    notes: str
    created_at: datetime


class AdminReservesResponse(Schema):
    reserves: List[AdminReserveItem]
    movements: List[AdminReserveMovementItem]


# ─── Quidax ──────────────────────────────────────────────────────────────────

class AdminQuidaxDepositItem(Schema):
    id: UUID
    user_email: str
    currency: str
    amount: Decimal
    status: str
    txid: str
    created_at: datetime


class AdminQuidaxWithdrawalItem(Schema):
    id: UUID
    user_email: str
    currency: str
    amount: Decimal
    status: str
    reference: str
    created_at: datetime


class AdminQuidaxWebhookItem(Schema):
    id: UUID
    event_type: str
    provider_event_id: str
    processed_at: Optional[datetime] = None
    created_at: datetime


class AdminQuidaxResponse(Schema):
    deposits: List[AdminQuidaxDepositItem]
    deposits_meta: PaginatedMeta
    withdrawals: List[AdminQuidaxWithdrawalItem]
    withdrawals_meta: PaginatedMeta
    webhooks: List[AdminQuidaxWebhookItem]


# ─── Generic ──────────────────────────────────────────────────────────────────

class MessageSchema(Schema):
    detail: str
