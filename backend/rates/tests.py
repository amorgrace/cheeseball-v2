from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from .models import Asset, RateConfiguration, RateQuote
from .schemas import RateQuoteSchema
from .services import build_quote


class RateQuoteSchemaTests(TestCase):
    def setUp(self):
        self.asset = Asset.objects.get(code="USDT")

    def make_quote(self, quote_type):
        return RateQuote.objects.create(
            asset=self.asset,
            quote_type=quote_type,
            market_rate=Decimal("1600.00"),
            markup_percent=Decimal("3.00") if quote_type == RateQuote.BUY else Decimal("2.00"),
            final_rate=Decimal("1648.00") if quote_type == RateQuote.BUY else Decimal("1568.00"),
            naira_amount=Decimal("10000.00"),
            crypto_amount=Decimal("6.06796116"),
            source="fallback",
            expires_at=timezone.now() + timedelta(minutes=10),
        )

    def test_buy_quote_schema_accepts_model_datetime(self):
        quote = self.make_quote(RateQuote.BUY)

        data = RateQuoteSchema.model_validate(quote, from_attributes=True)

        self.assertEqual(data.asset_code, "USDT")
        self.assertIsNotNone(data.expires_at)

    def test_sell_quote_schema_accepts_model_datetime(self):
        quote = self.make_quote(RateQuote.SELL)

        data = RateQuoteSchema.model_validate(quote, from_attributes=True)

        self.assertEqual(data.asset_code, "USDT")
        self.assertIsNotNone(data.expires_at)

    def test_btc_quote_rates_are_naira_per_dollar(self):
        btc, _ = Asset.objects.update_or_create(
            code="BTC",
            defaults={"name": "Bitcoin", "is_active": True, "binance_symbol": ""},
        )
        RateConfiguration.objects.update_or_create(
            asset=btc,
            defaults={
                "buy_markup_percent": Decimal("3.00"),
                "sell_markup_percent": Decimal("2.00"),
                "fallback_market_rate": Decimal("100000000.00"),
            },
        )

        buy_quote = build_quote(asset="BTC", quote_type=RateQuote.BUY, naira_amount=Decimal("103000.00"))
        sell_quote = build_quote(asset="BTC", quote_type=RateQuote.SELL, crypto_amount=Decimal("0.00100000"))

        self.assertEqual(buy_quote.market_rate, Decimal("1600.00"))
        self.assertEqual(buy_quote.final_rate, Decimal("1648.00"))
        self.assertEqual(buy_quote.crypto_usd_price, Decimal("62500.00000000"))
        self.assertEqual(buy_quote.crypto_amount, Decimal("0.00100000"))
        self.assertEqual(sell_quote.final_rate, Decimal("1568.00"))
        self.assertEqual(sell_quote.naira_amount, Decimal("98000.00"))


