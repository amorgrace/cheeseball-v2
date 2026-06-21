from django.core.cache import cache
from .models import Asset
from .schemas import BuyQuoteInputSchema, SellQuoteInputSchema
from .services import build_quote


def list_assets():
    cached_assets = cache.get("list_assets")
    if cached_assets is not None:
        return cached_assets
    assets = list(Asset.objects.filter(is_active=True))
    cache.set("list_assets", assets, 60 * 60)  # Cache for 1 hour
    return assets


def create_buy_quote(payload: BuyQuoteInputSchema):
    return build_quote(asset=payload.asset, quote_type="buy", crypto_amount=payload.crypto_amount, naira_amount=payload.naira_amount)


def create_sell_quote(payload: SellQuoteInputSchema):
    return build_quote(asset=payload.asset, quote_type="sell", crypto_amount=payload.crypto_amount, naira_amount=payload.naira_amount)
