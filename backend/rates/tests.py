from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from .models import Asset, RateQuote
from .schemas import RateQuoteSchema


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


