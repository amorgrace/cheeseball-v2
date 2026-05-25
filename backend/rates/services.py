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
USD_PRICE_PLACES = Decimal("0.00000001")
PERCENT_DIVISOR = Decimal("100")


def quantize_crypto(value: Decimal) -> Decimal:
    return value.quantize(SATOSHI_PLACES, rounding=ROUND_DOWN)


def quantize_naira(value: Decimal) -> Decimal:
    return value.quantize(NAIRA_PLACES, rounding=ROUND_DOWN)


def quantize_usd_price(value: Decimal) -> Decimal:
    return value.quantize(USD_PRICE_PLACES, rounding=ROUND_DOWN)


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


COINGECKO_IDS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "USDT": "tether",
    "USDC": "usd-coin",
    "BNB": "binancecoin",
    "SOL": "solana",
    "XRP": "ripple",
    "TRX": "tron",
    "LTC": "litecoin",
    "DOGE": "dogecoin",
    "BCH": "bitcoin-cash",
    "ADA": "cardano",
    "MATIC": "matic-network",
    "DOT": "polkadot",
    "LINK": "chainlink",
    "AVAX": "avalanche-2",
    "UNI": "uniswap",
    "XLM": "stellar",
    "ATOM": "cosmos",
    "TON": "the-open-network",
}


def get_live_usd_ngn_rate() -> tuple[Decimal, str]:
    import sys
    if "test" in sys.argv:
        return quantize_naira(Decimal(settings.USD_NGN_EXCHANGE_RATE)), "fallback"

    # 1. Try CoinGecko (Primary Live Source)
    try:
        from urllib.request import Request
        req = Request("https://api.coingecko.com/api/v3/simple/price?ids=tether&vs_currencies=ngn", headers={'User-Agent': 'Mozilla/5.0'})
        with urlopen(req, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        price = payload.get("tether", {}).get("ngn")
        if price is not None:
            return quantize_naira(Decimal(str(price))), "coingecko"
    except Exception:
        pass

    # 3. Safe fallback for testing/offline environments
    usd_ngn = Decimal(settings.USD_NGN_EXCHANGE_RATE)
    if usd_ngn > 0:
        return quantize_naira(usd_ngn), "fallback"

    raise ValidationError("Failed to fetch live USDT/NGN rate from CoinGecko")


def fetch_crypto_usd_price(asset: Asset) -> tuple[Decimal, str]:
    if asset.code in {"USDT", "USDC"}:
        return Decimal("1.00000000"), "stablecoin"

    import sys
    if "test" in sys.argv:
        fallback_rate = get_asset_fallback_rate(asset)
        usd_ngn = Decimal(settings.USD_NGN_EXCHANGE_RATE)
        return quantize_usd_price(fallback_rate / usd_ngn), "fallback"

    # 1. Try CoinGecko (Primary Live Source)
    coingecko_id = COINGECKO_IDS.get(asset.code.upper())
    if coingecko_id:
        try:
            from urllib.request import Request
            req = Request(f"https://api.coingecko.com/api/v3/simple/price?ids={coingecko_id}&vs_currencies=usd", headers={'User-Agent': 'Mozilla/5.0'})
            with urlopen(req, timeout=5) as response:
                payload = json.loads(response.read().decode("utf-8"))
            price = payload.get(coingecko_id, {}).get("usd")
            if price is not None:
                return quantize_usd_price(Decimal(str(price))), "coingecko"
        except Exception:
            pass

    # 3. Safe fallback for testing/offline environments
    fallback_rate = get_asset_fallback_rate(asset)
    if fallback_rate > 0:
        try:
            usd_ngn_exchange_rate = Decimal(settings.USD_NGN_EXCHANGE_RATE)
            return quantize_usd_price(fallback_rate / usd_ngn_exchange_rate), "fallback"
        except Exception:
            pass

    raise ValidationError(f"Failed to fetch live USD price for {asset.code} from CoinGecko")


def fetch_market_rate(asset: Asset) -> tuple[Decimal, str]:
    crypto_usd_price, source_crypto = fetch_crypto_usd_price(asset)
    usd_ngn_rate, source_fiat = get_live_usd_ngn_rate()
    if source_crypto == "stablecoin":
        source = source_fiat
    elif source_crypto == source_fiat:
        source = source_crypto
    else:
        source = f"{source_crypto}+{source_fiat}"
    return quantize_naira(crypto_usd_price * usd_ngn_rate), source


def build_quote(*, asset: str, quote_type: str, naira_amount: Decimal | None = None, crypto_amount: Decimal | None = None) -> RateQuote:
    asset_obj = get_asset(asset)
    config = get_rate_configuration(asset_obj)
    crypto_usd_price, crypto_source = fetch_crypto_usd_price(asset_obj)
    market_rate, fiat_source = get_live_usd_ngn_rate()
    buy_markup = Decimal(str(settings.BUY_MARKUP_PERCENT))
    sell_markup = Decimal(str(settings.SELL_MARKUP_PERCENT))

    if config:
        buy_markup = config.buy_markup_percent
        sell_markup = config.sell_markup_percent
        config.last_market_rate = quantize_naira(crypto_usd_price * market_rate)
        config.last_synced_at = timezone.now()
        config.save(update_fields=["last_market_rate", "last_synced_at", "updated_at"])

    if quote_type == RateQuote.BUY:
        markup_percent = buy_markup
        final_rate = quantize_naira(market_rate * (Decimal("1") + (markup_percent / PERCENT_DIVISOR)))
        if naira_amount is None:
            raise ValueError("naira_amount is required for buy quotes")
        if crypto_usd_price <= 0:
            raise ValidationError(f"USD price is not configured for {asset_obj.code}")
        crypto_amount = quantize_crypto((naira_amount / final_rate) / crypto_usd_price)
    else:
        markup_percent = sell_markup
        final_rate = quantize_naira(market_rate * (Decimal("1") - (markup_percent / PERCENT_DIVISOR)))
        if crypto_amount is None and naira_amount is None:
            raise ValueError("Either crypto_amount or naira_amount is required for sell quotes")
        
        if crypto_amount is not None:
            naira_amount = quantize_naira(crypto_amount * crypto_usd_price * final_rate)
        else:
            if crypto_usd_price <= 0:
                raise ValidationError(f"USD price is not configured for {asset_obj.code}")
            crypto_amount = quantize_crypto((naira_amount / final_rate) / crypto_usd_price)

    if crypto_source == "stablecoin":
        source = fiat_source
    elif crypto_source == fiat_source:
        source = crypto_source
    else:
        source = f"{crypto_source}+{fiat_source}"

    return RateQuote.objects.create(
        asset=asset_obj,
        quote_type=quote_type,
        market_rate=market_rate,
        markup_percent=markup_percent,
        final_rate=final_rate,
        crypto_usd_price=crypto_usd_price,
        naira_amount=naira_amount,
        crypto_amount=crypto_amount,
        source=source,
        expires_at=timezone.now() + timedelta(minutes=settings.QUOTE_TTL_MINUTES),
    )
