import hashlib
import hmac
import json
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from broker.models import Transaction
from payouts.models import BeneficiaryBankAccount
from rates.models import Asset, RateQuote
from wallets.models import PlatformReserve, WalletBalance

from .models import QuidaxDeposit, QuidaxSubAccount, QuidaxWalletAddress, QuidaxWebhookEvent
from .services import create_pending_sell_deposit, process_webhook, verify_webhook_signature


class QuidaxWebhookTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(email="seller@example.com", password="secret123")
        self.asset, _ = Asset.objects.update_or_create(
            code="BTC",
            defaults={"name": "Bitcoin", "is_active": True},
        )
        self.ngn_asset, _ = Asset.objects.update_or_create(
            code="NGN",
            defaults={"name": "Nigerian Naira", "is_active": True},
        )
        self.account = QuidaxSubAccount.objects.create(
            user=self.user,
            quidax_id="quidax-user-1",
            email=self.user.email,
        )
        self.address = QuidaxWalletAddress.objects.create(
            user=self.user,
            sub_account=self.account,
            currency="BTC",
            network="Bitcoin",
            address="bc1qquidaxwallet123",
            status=QuidaxWalletAddress.GENERATED,
        )

    @override_settings(QUIDAX_WEBHOOK_SECRET="webhook-secret")
    def test_verify_webhook_signature_accepts_timestamped_hmac(self):
        raw_body = b'{"event":"deposit.successful"}'
        timestamp = "1710000000"
        signature = hmac.new(
            b"webhook-secret",
            timestamp.encode("utf-8") + b"." + raw_body,
            hashlib.sha256,
        ).hexdigest()

        self.assertTrue(verify_webhook_signature(raw_body, signature, timestamp))

    def test_wallet_deposit_successful_is_idempotent(self):
        payload = {
            "id": "evt-1",
            "event": "deposit.successful",
            "data": {
                "id": "dep-1",
                "user": {"id": self.account.quidax_id},
                "currency": "BTC",
                "network": "Bitcoin",
                "amount": "0.00100000",
                "txid": "tx-1",
            },
        }

        first = process_webhook(payload, signature="sig")
        second = process_webhook(payload, signature="sig")

        wallet = WalletBalance.objects.get(user=self.user, asset=self.asset)
        reserve = PlatformReserve.objects.get(asset=self.asset)
        self.assertTrue(first["credited"])
        self.assertTrue(second["duplicate"])
        self.assertEqual(wallet.balance, Decimal("0.00100000"))
        self.assertEqual(reserve.balance, Decimal("0.00100000"))
        self.assertEqual(QuidaxWebhookEvent.objects.count(), 1)

    def test_sell_deposit_auto_completes_transaction_without_crediting_crypto_wallet(self):
        beneficiary = BeneficiaryBankAccount.objects.create(
            user=self.user,
            account_name="Jane Doe",
            bank_name="Demo Bank",
            account_number="0123456789",
            account_type=BeneficiaryBankAccount.SAVINGS,
        )
        quote = RateQuote.objects.create(
            asset=self.asset,
            quote_type=RateQuote.SELL,
            market_rate=Decimal("100000000.00"),
            markup_percent=Decimal("2.00"),
            final_rate=Decimal("98000000.00"),
            naira_amount=Decimal("98000.00"),
            crypto_amount=Decimal("0.00100000"),
            source="fallback",
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        transaction_obj = Transaction.objects.create(
            user=self.user,
            quote=quote,
            transaction_type=Transaction.SELL,
            asset=self.asset,
            status=Transaction.PENDING_PAYMENT,
            naira_amount=quote.naira_amount,
            crypto_amount=quote.crypto_amount,
            market_rate=quote.market_rate,
            markup_percent=quote.markup_percent,
            final_rate=quote.final_rate,
            broker_wallet_address=self.address.address,
            crypto_source=Transaction.CRYPTO_SOURCE_EXTERNAL,
            payout_method=Transaction.PAYOUT_BANK,
            bank_name=beneficiary.bank_name,
            bank_account_name=beneficiary.account_name,
            bank_account_number=beneficiary.account_number,
            bank_account_type=beneficiary.account_type,
        )
        PlatformReserve.objects.create(asset=self.asset, balance=Decimal("0.00000000"))
        pending_deposit = create_pending_sell_deposit(transaction_obj=transaction_obj, wallet_address=self.address)

        payload = {
            "id": "evt-sell",
            "event": "deposit.successful",
            "data": {
                "id": "dep-sell",
                "user": {"id": self.account.quidax_id},
                "currency": "BTC",
                "network": "Bitcoin",
                "amount": "0.00100000",
                "txid": "tx-sell",
            },
        }

        result = process_webhook(payload, signature="sig")

        transaction_obj.refresh_from_db()
        pending_deposit.refresh_from_db()
        self.assertTrue(result["credited"])
        self.assertEqual(transaction_obj.status, Transaction.COMPLETED)
        self.assertTrue(transaction_obj.finalized)
        self.assertEqual(pending_deposit.status, QuidaxDeposit.SUCCESSFUL)
        btc_wallet = WalletBalance.objects.filter(user=self.user, asset=self.asset).first()
        self.assertIn(btc_wallet.balance if btc_wallet else Decimal("0.00000000"), {Decimal("0E-8"), Decimal("0.00000000")})
        self.assertEqual(PlatformReserve.objects.get(asset=self.asset).balance, Decimal("0.00100000"))
