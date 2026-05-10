from datetime import datetime
from decimal import Decimal

from ninja import Schema
from pydantic import model_validator


class BuyQuoteInputSchema(Schema):
    asset: str
    naira_amount: Decimal

    @model_validator(mode="after")
    def validate_amount(self):
        self.asset = self.asset.strip().upper()
        if self.naira_amount <= 0:
            raise ValueError("naira_amount must be greater than zero")
        return self


class SellQuoteInputSchema(Schema):
    asset: str
    crypto_amount: Decimal

    @model_validator(mode="after")
    def validate_amount(self):
        self.asset = self.asset.strip().upper()
        if self.crypto_amount <= 0:
            raise ValueError("crypto_amount must be greater than zero")
        return self


class AssetSchema(Schema):
    code: str
    name: str
    network: str
    broker_wallet_address: str
    is_active: bool


class RateQuoteSchema(Schema):
    id: int
    asset_code: str
    asset_name: str
    quote_type: str
    market_rate: Decimal
    markup_percent: Decimal
    final_rate: Decimal
    crypto_usd_price: Decimal
    naira_amount: Decimal | None = None
    crypto_amount: Decimal | None = None
    source: str
    expires_at: datetime
