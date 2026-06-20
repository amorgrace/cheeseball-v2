from datetime import datetime
from decimal import Decimal
from uuid import UUID

from ninja import Schema
from pydantic import model_validator


class TransferCreateSchema(Schema):
    transfer_type: str  # 'internal' or 'external'
    asset: str
    amount: Decimal
    
    # Internal specific (either email or id)
    recipient_email: str | None = None
    recipient_id: UUID | None = None
    
    # External specific
    recipient_address: str | None = None
    recipient_network: str | None = None

    @model_validator(mode="after")
    def validate_fields(self):
        if self.amount <= 0:
            raise ValueError("Amount must be greater than 0.")
        if not self.asset:
            raise ValueError("Asset is required.")
            
        if self.transfer_type == "internal":
            if not self.recipient_email and not self.recipient_id:
                raise ValueError("recipient_email or recipient_id is required for internal transfers.")
        elif self.transfer_type == "external":
            if not self.recipient_address:
                raise ValueError("recipient_address is required for external transfers.")
        else:
            raise ValueError("transfer_type must be 'internal' or 'external'.")
            
        return self


class TransferResponseSchema(Schema):
    id: UUID
    transfer_type: str
    asset: str
    amount: Decimal
    status: str
    
    recipient_email: str | None = None
    recipient_address: str | None = None
    recipient_network: str | None = None
    
    failure_reason: str
    admin_notes: str
    
    created_at: datetime
    reviewed_at: datetime | None = None
    completed_at: datetime | None = None


class AdminTransferActionSchema(Schema):
    reason: str | None = None
