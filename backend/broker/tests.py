import json
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from broker.models import Transaction
from broker.views import complete_transaction, create_sell_transaction
from payouts.models import BeneficiaryBankAccount
from rates.models import Asset, RateQuote


class BrokerFlowTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(email="seller@example.com", password="secret123")
        self.other_user = user_model.objects.create_user(email="other@example.com", password="secret123")
        self.admin = user_model.objects.create_user(
            email="admin@example.com",
            password="secret123",
            is_staff=True,
        )
        self.asset, _ = Asset.objects.update_or_create(
            code="BTC",
            defaults={
                "name": "Bitcoin",
                "is_active": True,
                "broker_wallet_address": "bc1qbrokerwallet123",
            },
        )
        self.buy_quote = RateQuote.objects.create(
            asset=self.asset,
            quote_type=RateQuote.BUY,
            market_rate=Decimal("100000000.00"),
            markup_percent=Decimal("3.00"),
            final_rate=Decimal("103000000.00"),
            naira_amount=Decimal("103000.00"),
            crypto_amount=Decimal("0.00100000"),
            source="fallback",
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        self.sell_quote = RateQuote.objects.create(
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
        self.buy_transaction = Transaction.objects.create(
            user=self.user,
            quote=self.buy_quote,
            transaction_type=Transaction.BUY,
            asset=self.asset,
            status=Transaction.PENDING_PAYMENT,
            payment_method=Transaction.BANK_TRANSFER,
            naira_amount=self.buy_quote.naira_amount,
            crypto_amount=self.buy_quote.crypto_amount,
            market_rate=self.buy_quote.market_rate,
            markup_percent=self.buy_quote.markup_percent,
            final_rate=self.buy_quote.final_rate,
            wallet_address="0xabc123",
            network="BTC",
        )

    def make_request(self, user):
        return SimpleNamespace(auth=user)

    def test_admin_cannot_complete_unpaid_buy_transaction(self):
        payload = SimpleNamespace(note="Sent manually")

        response = complete_transaction(self.make_request(self.admin), self.buy_transaction.id, payload)

        self.buy_transaction.refresh_from_db()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            json.loads(response.content)["detail"],
            "['Cannot change transaction status from pending_payment to completed']",
        )
        self.assertEqual(self.buy_transaction.status, Transaction.PENDING_PAYMENT)

    def test_create_sell_transaction_uses_saved_beneficiary(self):
        beneficiary = BeneficiaryBankAccount.objects.create(
            user=self.user,
            account_name="Jane Doe",
            bank_name="Demo Bank",
            account_number="0123456789",
            account_type=BeneficiaryBankAccount.SAVINGS,
        )

        transaction = create_sell_transaction(
            self.make_request(self.user),
            SimpleNamespace(quote_id=self.sell_quote.id, beneficiary_id=beneficiary.id),
        )

        self.assertIsInstance(transaction, Transaction)
        self.assertEqual(transaction.transaction_type, Transaction.SELL)
        self.assertEqual(transaction.bank_name, beneficiary.bank_name)
        self.assertEqual(transaction.bank_account_name, beneficiary.account_name)
        self.assertEqual(transaction.bank_account_number, beneficiary.account_number)
        self.assertEqual(transaction.bank_account_type, beneficiary.account_type)
        self.assertEqual(transaction.broker_wallet_address, "bc1qbrokerwallet123")

    def test_create_sell_transaction_rejects_beneficiary_from_another_user(self):
        beneficiary = BeneficiaryBankAccount.objects.create(
            user=self.other_user,
            account_name="Other User",
            bank_name="Other Bank",
            account_number="9999999999",
            account_type=BeneficiaryBankAccount.CHECKING,
        )

        response = create_sell_transaction(
            self.make_request(self.user),
            SimpleNamespace(quote_id=self.sell_quote.id, beneficiary_id=beneficiary.id),
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            json.loads(response.content)["detail"],
            "['Beneficiary bank account not found']",
        )
