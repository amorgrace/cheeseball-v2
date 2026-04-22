import json
from decimal import Decimal
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import TestCase

from rates.models import Asset, RateConfiguration
from wallets.services import get_user_wallet
from wallets.views import execute_conversion, get_balance_summary, preview_conversion


class WalletConversionTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(email="wallet@example.com", password="secret123")

        self.ngn_asset, _ = Asset.objects.update_or_create(
            code="NGN",
            defaults={"name": "Naira", "is_active": True, "binance_symbol": ""},
        )
        self.btc_asset, _ = Asset.objects.update_or_create(
            code="BTC",
            defaults={"name": "Bitcoin", "is_active": True, "binance_symbol": ""},
        )
        RateConfiguration.objects.update_or_create(
            asset=self.btc_asset,
            defaults={
                "buy_markup_percent": Decimal("3.00"),
                "sell_markup_percent": Decimal("2.00"),
                "fallback_market_rate": Decimal("100000000.00"),
            },
        )

    def make_request(self):
        return SimpleNamespace(auth=self.user)

    def test_preview_ngn_to_btc_creates_rate_lock(self):
        response = preview_conversion(
            self.make_request(),
            SimpleNamespace(from_asset="NGN", to_asset="BTC", from_amount=Decimal("103000.00")),
        )

        self.assertEqual(response["from_asset"], "NGN")
        self.assertEqual(response["to_asset"], "BTC")
        self.assertEqual(response["rate"], Decimal("103000000.00"))
        self.assertEqual(response["to_amount"], Decimal("0.00100000"))
        self.assertIn("rate_lock_id", response)

    def test_execute_conversion_moves_balances_for_btc_to_ngn(self):
        btc_wallet = get_user_wallet(self.user, self.btc_asset)
        btc_wallet.balance = Decimal("0.00100000")
        btc_wallet.save(update_fields=["balance", "updated_at"])

        preview = preview_conversion(
            self.make_request(),
            SimpleNamespace(from_asset="BTC", to_asset="NGN", from_amount=Decimal("0.00100000")),
        )

        result = execute_conversion(
            self.make_request(),
            SimpleNamespace(rate_lock_id=preview["rate_lock_id"]),
        )

        btc_wallet.refresh_from_db()
        ngn_wallet = get_user_wallet(self.user, self.ngn_asset)
        ngn_wallet.refresh_from_db()

        self.assertEqual(result["status"], "completed")
        self.assertEqual(btc_wallet.balance, Decimal("0E-8"))
        self.assertEqual(ngn_wallet.balance, Decimal("98000.00"))

    def test_preview_rejects_crypto_to_crypto_conversion(self):
        eth_asset, _ = Asset.objects.update_or_create(
            code="ETH",
            defaults={"name": "Ethereum", "is_active": True, "binance_symbol": ""},
        )
        RateConfiguration.objects.update_or_create(
            asset=eth_asset,
            defaults={
                "buy_markup_percent": Decimal("3.00"),
                "sell_markup_percent": Decimal("2.00"),
                "fallback_market_rate": Decimal("5000000.00"),
            },
        )

        response = preview_conversion(
            self.make_request(),
            SimpleNamespace(from_asset="BTC", to_asset="ETH", from_amount=Decimal("0.00100000")),
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            json.loads(response.content)["detail"],
            "['Only NGN to crypto or crypto to NGN conversions are supported']",
        )

    def test_balance_summary_returns_portfolio_value_and_real_ngn_wallet(self):
        ngn_wallet = get_user_wallet(self.user, self.ngn_asset)
        ngn_wallet.balance = Decimal("20000.00")
        ngn_wallet.save(update_fields=["balance", "updated_at"])

        btc_wallet = get_user_wallet(self.user, self.btc_asset)
        btc_wallet.balance = Decimal("0.00100000")
        btc_wallet.save(update_fields=["balance", "updated_at"])

        summary = get_balance_summary(self.make_request())

        self.assertEqual(summary["ngn_wallet_balance"], "20000.00")
        self.assertEqual(summary["ngn_wallet_available_balance"], "20000.00")
        self.assertEqual(summary["estimated_portfolio_value"], "120000.00")
        self.assertEqual(summary["estimated_available_value"], "120000.00")
        self.assertEqual(summary["total_balance"], "120000.00")
