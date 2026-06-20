from datetime import datetime
from uuid import UUID

from ninja import Schema


class QuidaxSubAccountSchema(Schema):
    quidax_id: str
    email: str


class QuidaxWalletAddressCreateSchema(Schema):
    currency: str
    network: str | None = None


class QuidaxWalletAddressSchema(Schema):
    id: UUID
    currency: str
    network: str
    address: str
    destination_tag: str
    status: str
    created_at: datetime
    updated_at: datetime


class QuidaxWalletBalanceSchema(Schema):
    currency: str
    balance: str
    locked: str
    staked: str


class QuidaxDiagnosticSchema(Schema):
    configured: bool
    base_url: str
    user: dict


class QuidaxWebhookResponseSchema(Schema):
    message: str
    event_type: str | None = None
    event_id: str | None = None
    duplicate: bool | None = None
    ignored: bool | None = None
    reason: str | None = None
    credited: bool | None = None
    asset: str | None = None
    amount: str | None = None
    deposit_id: str | None = None
    currency: str | None = None
    address: str | None = None
