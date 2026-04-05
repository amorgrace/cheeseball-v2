import json
from datetime import timedelta
from decimal import Decimal, ROUND_DOWN
from urllib.error import URLError
from urllib.request import urlopen

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

from .constants import ASSET_SEED_BY_CODE
from .models import Asset, RateConfiguration, RateQuote

SATOSHI_PLACES = Decimal("0.00000001")
NAIRA_PLACES = Decimal("0.01")
PERCENT_DIVISOR = Decimal("100")


def quantize_crypto(value: Decimal) -> Decimal:
    return value.quantize(SATOSHI_PLACES, rounding=ROUND_DOWN)


def quantize_naira(value: Decimal) -> Decimal:
    return value.quantize(NAIRA_PLACES, rounding=ROUND_DOWN)


def get_asset(code: str) -> Asset:
    asset = Asset.objects.filter(code=code, is_active=True).first()
    if not asset:
        raise ValidationError("Asset not found or inactive")
    return asset


def get_rate_configuration(asset: Asset) -> RateConfiguration | None:
    defaults = {
        "buy_markup_percent": Decimal(str(settings.BUY_MARKUP_PERCENT)),
        "sell_markup_percent": Decimal(str(settings.SELL_MARKUP_PERCENT)),
        "fallback_market_rate": Decimal(str(ASSET_SEED_BY_CODE.get(asset.code, {}).get("fallback_market_rate", "0"))),
    }
    config, _created = RateConfiguration.objects.get_or_create(asset=asset, defaults=defaults)
    return config


def get_asset_fallback_rate(asset: Asset) -> Decimal:
    config = RateConfiguration.objects.filter(asset=asset).first()
    if config:
        return config.fallback_market_rate
    return Decimal("0.00")


def fetch_market_rate(asset: Asset) -> tuple[Decimal, str]:
    symbol = asset.binance_symbol
    if not symbol:
        return get_asset_fallback_rate(asset), "fallback"
    try:
        with urlopen(settings.BINANCE_PRICE_URL_TEMPLATE.format(symbol=symbol), timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        usd_price = Decimal(str(payload["price"]))
        usd_ngn_rate = Decimal(str(settings.USD_NGN_EXCHANGE_RATE))
        market_rate = quantize_naira(usd_price * usd_ngn_rate)
        return market_rate, "binance"
    except (KeyError, ValueError, TypeError, URLError, TimeoutError):
        return get_asset_fallback_rate(asset), "fallback"


def build_quote(*, asset: str, quote_type: str, naira_amount: Decimal | None = None, crypto_amount: Decimal | None = None) -> RateQuote:
    asset_obj = get_asset(asset)
    config = get_rate_configuration(asset_obj)
    market_rate, source = fetch_market_rate(asset_obj)
    buy_markup = Decimal(str(settings.BUY_MARKUP_PERCENT))
    sell_markup = Decimal(str(settings.SELL_MARKUP_PERCENT))

    if config:
        buy_markup = config.buy_markup_percent
        sell_markup = config.sell_markup_percent
        config.last_market_rate = market_rate
        config.last_synced_at = timezone.now()
        config.save(update_fields=["last_market_rate", "last_synced_at", "updated_at"])

    if quote_type == RateQuote.BUY:
        markup_percent = buy_markup
        final_rate = quantize_naira(market_rate * (Decimal("1") + (markup_percent / PERCENT_DIVISOR)))
        if naira_amount is None:
            raise ValueError("naira_amount is required for buy quotes")
        crypto_amount = quantize_crypto(naira_amount / final_rate)
    else:
        markup_percent = sell_markup
        final_rate = quantize_naira(market_rate * (Decimal("1") - (markup_percent / PERCENT_DIVISOR)))
        if crypto_amount is None:
            raise ValueError("crypto_amount is required for sell quotes")
        naira_amount = quantize_naira(crypto_amount * final_rate)

    return RateQuote.objects.create(
        asset=asset_obj,
        quote_type=quote_type,
        market_rate=market_rate,
        markup_percent=markup_percent,
        final_rate=final_rate,
        naira_amount=naira_amount,
        crypto_amount=crypto_amount,
        source=source,
        expires_at=timezone.now() + timedelta(minutes=settings.QUOTE_TTL_MINUTES),
    )
