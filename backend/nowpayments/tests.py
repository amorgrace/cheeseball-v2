import hashlib
import hmac
import json
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from rates.models import Asset
from wallets.models import Ledger, PlatformReserve, WalletBalance

from .models import CustodyAccount, CustodyDeposit
from .services import create_custody_deposit, ensure_custody_account, verify_ipn_signature
from .views import custody_balance, diagnostics, nowpayments_ipn


class NowPaymentsTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user("user@example.com", password="secret")

    def make_payload(self):
        return SimpleNamespace(
            payment_id=12345,
            payment_status="finished",
            order_id="tx-123",
            dict=lambda exclude_none=True: {
                "payment_id": 12345,
                "payment_status": "finished",
                "order_id": "tx-123",
            },
        )

    @override_settings(NOWPAYMENTS_IPN_SECRET="secret")
    def test_verify_ipn_signature_accepts_sorted_payload_hmac(self):
        payload = {
            "payment_status": "finished",
            "payment_id": 12345,
            "order_id": "tx-123",
        }
        canonical = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        signature = hmac.new(b"secret", canonical, hashlib.sha512).hexdigest()

        self.assertTrue(verify_ipn_signature(payload, signature))

    @override_settings(NOWPAYMENTS_IPN_SECRET="secret")
    def test_ipn_rejects_invalid_signature(self):
        response = nowpayments_ipn(SimpleNamespace(), self.make_payload(), "bad")

        self.assertEqual(response.status_code, 401)

    @override_settings(NOWPAYMENTS_IPN_SECRET="secret")
    def test_ipn_accepts_valid_signature_and_ignores_unknown_payment(self):
        payload = self.make_payload()
        body = payload.dict()
        canonical = json.dumps(body, separators=(",", ":"), sort_keys=True).encode("utf-8")
        signature = hmac.new(b"secret", canonical, hashlib.sha512).hexdigest()

        response = nowpayments_ipn(SimpleNamespace(), payload, signature)

        self.assertEqual(response["message"], "NOWPayments IPN ignored")
        self.assertEqual(response["reason"], "unknown payment")

    @override_settings(NOWPAYMENTS_IPN_SECRET="secret")
    def test_finished_ipn_credits_internal_wallet_once(self):
        asset, _created = Asset.objects.update_or_create(
            code="USDT",
            defaults={"name": "Tether", "is_active": True},
        )
        account = CustodyAccount.objects.create(user=self.user, sub_partner_id="1631380403", name="cb-user")
        deposit = CustodyDeposit.objects.create(
            user=self.user,
            custody_account=account,
            currency="usdt",
            amount=Decimal("1.20000000"),
            provider_payment_id="12345",
            payment_status=CustodyDeposit.PENDING,
        )
        body_dict = {
            "payment_id": 12345,
            "payment_status": "finished",
            "actually_paid": "1.20000000",
            "pay_currency": "usdt",
        }
        body = json.dumps(body_dict).encode("utf-8")
        canonical = json.dumps(body_dict, separators=(",", ":"), sort_keys=True).encode("utf-8")
        signature = hmac.new(b"secret", canonical, hashlib.sha512).hexdigest()
        payload = SimpleNamespace(
            payment_id=12345,
            payment_status="finished",
            order_id=None,
            dict=lambda exclude_none=True: body_dict,
        )

        response = nowpayments_ipn(SimpleNamespace(body=body), payload, signature)
        duplicate_response = nowpayments_ipn(SimpleNamespace(body=body), payload, signature)

        deposit.refresh_from_db()
        wallet = WalletBalance.objects.get(user=self.user, asset=asset)
        reserve = PlatformReserve.objects.get(asset=asset)
        self.assertTrue(response["credited"])
        self.assertTrue(duplicate_response["already_credited"])
        self.assertEqual(deposit.payment_status, CustodyDeposit.FINISHED)
        self.assertIsNotNone(deposit.credited_at)
        self.assertEqual(wallet.balance, Decimal("1.20000000"))
        self.assertEqual(reserve.balance, Decimal("1.20000000"))
        self.assertEqual(
            Ledger.objects.filter(user=self.user, wallet_balance=wallet, transaction_type=Ledger.WALLET_DEPOSIT).count(),
            1,
        )

    @override_settings(NOWPAYMENTS_API_KEY="api-key", NOWPAYMENTS_IPN_SECRET="secret")
    @patch("nowpayments.services._nowpayments_request")
    def test_diagnostics_requires_admin_and_returns_provider_checks(self, request_mock):
        user_model = get_user_model()
        admin = user_model.objects.create_user("admin@example.com", password="secret", is_staff=True)
        request_mock.side_effect = [
            {"message": "OK"},
            {"currencies": ["btc"]},
            {"btc": {"amount": "0"}},
        ]

        response = diagnostics(SimpleNamespace(auth=admin))

        self.assertTrue(response["configured"])
        self.assertEqual(response["status"], {"message": "OK"})
        self.assertEqual(response["balance"], {"btc": {"amount": "0"}})

    def test_diagnostics_rejects_non_admin(self):
        response = diagnostics(SimpleNamespace(auth=self.user))

        self.assertEqual(response.status_code, 403)

    @override_settings(
        NOWPAYMENTS_API_KEY="api-key",
        NOWPAYMENTS_EMAIL="merchant@example.com",
        NOWPAYMENTS_PASSWORD="password",
    )
    @patch("nowpayments.services.authenticate_nowpayments")
    @patch("nowpayments.services._nowpayments_request")
    def test_ensure_custody_account_creates_sub_partner(self, request_mock, auth_mock):
        auth_mock.return_value = "jwt-token"
        request_mock.return_value = {
            "id": "1631380403",
            "name": "cb-user",
        }

        account = ensure_custody_account(self.user)

        self.assertEqual(account.sub_partner_id, "1631380403")
        self.assertTrue(CustodyAccount.objects.filter(user=self.user).exists())
        request_mock.assert_called_once()
        path, kwargs = request_mock.call_args.args[0], request_mock.call_args.kwargs
        self.assertEqual(path, "sub-partner/balance")
        self.assertTrue(kwargs["data"]["name"].startswith("cb-"))
        self.assertLessEqual(len(kwargs["data"]["name"]), 30)
        self.assertEqual(kwargs["method"], "POST")
        self.assertEqual(kwargs["bearer_token"], "jwt-token")

    @override_settings(
        NOWPAYMENTS_API_KEY="api-key",
        NOWPAYMENTS_EMAIL="merchant@example.com",
        NOWPAYMENTS_PASSWORD="password",
    )
    @patch("nowpayments.services.authenticate_nowpayments")
    @patch("nowpayments.services._nowpayments_request")
    def test_create_custody_deposit_generates_top_up_payment(self, request_mock, auth_mock):
        auth_mock.return_value = "jwt-token"
        CustodyAccount.objects.create(user=self.user, sub_partner_id="1631380403", name="cb-user")
        request_mock.return_value = {
            "payment_id": "pay-123",
            "pay_address": "TExampleAddress",
            "pay_amount": "0.30000000",
            "payment_status": "waiting",
        }

        deposit = create_custody_deposit(self.user, currency="TRX", amount="0.3")

        self.assertEqual(deposit.provider_payment_id, "pay-123")
        self.assertEqual(deposit.pay_address, "TExampleAddress")
        self.assertEqual(deposit.payment_status, "waiting")
        self.assertTrue(CustodyDeposit.objects.filter(user=self.user).exists())
        request_mock.assert_called_once()
        _path, kwargs = request_mock.call_args.args[0], request_mock.call_args.kwargs
        self.assertEqual(_path, "sub-partner/payment")
        self.assertEqual(kwargs["data"]["currency"], "trx")
        self.assertEqual(kwargs["data"]["sub_partner_id"], "1631380403")

    @override_settings(
        NOWPAYMENTS_API_KEY="api-key",
        NOWPAYMENTS_EMAIL="merchant@example.com",
        NOWPAYMENTS_PASSWORD="password",
    )
    @patch("nowpayments.views.get_custody_balance")
    def test_custody_balance_returns_account_and_provider_balance(self, balance_mock):
        CustodyAccount.objects.create(user=self.user, sub_partner_id="1631380403", name="cb-user")
        balance_mock.return_value = {"balances": {"trx": {"amount": "1.5"}}}

        response = custody_balance(SimpleNamespace(auth=self.user))

        self.assertEqual(response["account"]["sub_partner_id"], "1631380403")
        self.assertEqual(response["provider_balance"]["balances"]["trx"]["amount"], "1.5")
