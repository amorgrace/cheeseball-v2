import json
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from broker.models import Transaction
from broker.views import approve_transaction, complete_transaction, create_buy_transaction, create_sell_transaction
from payouts.models import BeneficiaryBankAccount
from rates.models import Asset, RateQuote
from broker.services import transition_transaction, _finalize_transaction
from quidax.models import QuidaxDeposit, QuidaxSubAccount, QuidaxWalletAddress
from wallets.models import PlatformReserve, ReserveMovement, Ledger as WalletLedger, WalletBalance


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
        self.quidax_account = QuidaxSubAccount.objects.create(
            user=self.user,
            quidax_id="quidax-user-1",
            email=self.user.email,
        )
        self.quidax_wallet_address = QuidaxWalletAddress.objects.create(
            user=self.user,
            sub_account=self.quidax_account,
            currency="BTC",
            network="Bitcoin",
            address="bc1qquidaxwallet123",
            status=QuidaxWalletAddress.GENERATED,
        )
        self.quidax_address_patcher = patch("quidax.services.ensure_wallet_address", return_value=self.quidax_wallet_address)
        self.quidax_address_patcher.start()
        self.addCleanup(self.quidax_address_patcher.stop)
        self.asset, _ = Asset.objects.update_or_create(
            code="BTC",
            defaults={
                "name": "Bitcoin",
                "is_active": True,
                "broker_wallet_address": "bc1qbrokerwallet123",
            },
        )
        self.ngn_asset, _ = Asset.objects.update_or_create(
            code="NGN",
            defaults={
                "name": "Nigerian Naira",
                "is_active": True,
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
        self.manual_asset, _ = Asset.objects.update_or_create(
            code="SOL",
            defaults={
                "name": "Solana",
                "is_active": True,
                "broker_wallet_address": "solbrokerwallet123",
            },
        )
        self.manual_buy_quote = RateQuote.objects.create(
            asset=self.manual_asset,
            quote_type=RateQuote.BUY,
            market_rate=Decimal("1600.00"),
            markup_percent=Decimal("3.00"),
            final_rate=Decimal("1648.00"),
            naira_amount=Decimal("164800.00"),
            crypto_amount=Decimal("1.00000000"),
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

    def test_create_buy_transaction_with_ngn_wallet_debits_wallet_and_marks_paid(self):
        WalletBalance.objects.update_or_create(
            user=self.user,
            asset=self.ngn_asset,
            defaults={"balance": Decimal("150000.00")},
        )

        transaction = create_buy_transaction(
            self.make_request(self.user),
            SimpleNamespace(
                quote_id=self.buy_quote.id,
                wallet_address="0xabc123",
                network="BTC",
                payment_method=Transaction.NGN_WALLET,
            ),
        )

        wallet = WalletBalance.objects.get(user=self.user, asset=self.ngn_asset)
        self.assertIsInstance(transaction, Transaction)
        self.assertEqual(transaction.status, Transaction.PAID)
        self.assertEqual(transaction.payment_method, Transaction.NGN_WALLET)
        self.assertEqual(wallet.balance, Decimal("47000.00000000"))
        self.assertTrue(
            WalletLedger.objects.filter(
                user=self.user,
                wallet_balance=wallet,
                transaction_type=WalletLedger.BUY_PAYMENT,
                reference_id=transaction.id,
            ).exists()
        )

    def test_create_buy_transaction_with_ngn_wallet_rejects_insufficient_balance(self):
        WalletBalance.objects.update_or_create(
            user=self.user,
            asset=self.ngn_asset,
            defaults={"balance": Decimal("50000.00")},
        )

        response = create_buy_transaction(
            self.make_request(self.user),
            SimpleNamespace(
                quote_id=self.buy_quote.id,
                wallet_address="0xabc123",
                network="BTC",
                payment_method=Transaction.NGN_WALLET,
            ),
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Transaction.objects.filter(payment_method=Transaction.NGN_WALLET).exists())

    def test_create_automated_asset_buy_rejects_manual_bank_transfer(self):
        response = create_buy_transaction(
            self.make_request(self.user),
            SimpleNamespace(
                quote_id=self.buy_quote.id,
                wallet_address="0xabc123",
                network="BTC",
                payment_method=Transaction.BANK_TRANSFER,
            ),
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            json.loads(response.content)["detail"],
            "['BTC purchases support Paystack bank transfer or NGN wallet only.']",
        )

    def test_create_automated_asset_buy_accepts_paystack_bank_transfer(self):
        transaction = create_buy_transaction(
            self.make_request(self.user),
            SimpleNamespace(
                quote_id=self.buy_quote.id,
                wallet_address="0xabc123",
                network="BTC",
                payment_method=Transaction.PAYSTACK,
            ),
        )

        self.assertIsInstance(transaction, Transaction)
        self.assertEqual(transaction.status, Transaction.PENDING_PAYMENT)
        self.assertEqual(transaction.payment_method, Transaction.PAYSTACK)

    def test_create_manual_asset_buy_rejects_automated_payment_method(self):
        response = create_buy_transaction(
            self.make_request(self.user),
            SimpleNamespace(
                quote_id=self.manual_buy_quote.id,
                wallet_address="soladdress123",
                network="Solana",
                payment_method=Transaction.PAYSTACK,
            ),
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            json.loads(response.content)["detail"],
            "['SOL purchases require manual bank transfer.']",
        )

    def test_create_manual_asset_buy_accepts_manual_bank_transfer(self):
        transaction = create_buy_transaction(
            self.make_request(self.user),
            SimpleNamespace(
                quote_id=self.manual_buy_quote.id,
                wallet_address="soladdress123",
                network="Solana",
                payment_method=Transaction.BANK_TRANSFER,
            ),
        )

        self.assertIsInstance(transaction, Transaction)
        self.assertEqual(transaction.status, Transaction.PENDING_PAYMENT)
        self.assertEqual(transaction.payment_method, Transaction.BANK_TRANSFER)

    def create_beneficiary(self):
        return BeneficiaryBankAccount.objects.create(
            user=self.user,
            account_name="Jane Doe",
            bank_name="Demo Bank",
            account_number="0123456789",
            account_type=BeneficiaryBankAccount.SAVINGS,
        )

    def test_create_external_sell_transaction_uses_saved_beneficiary_without_locking_crypto(self):
        beneficiary = self.create_beneficiary()

        transaction = create_sell_transaction(
            self.make_request(self.user),
            SimpleNamespace(
                quote_id=self.sell_quote.id,
                payout_method=Transaction.PAYOUT_BANK,
                beneficiary_id=beneficiary.id,
                network="Bitcoin",
            ),
        )

        self.assertIsInstance(transaction, Transaction)
        self.assertEqual(transaction.transaction_type, Transaction.SELL)
        self.assertEqual(transaction.crypto_source, Transaction.CRYPTO_SOURCE_EXTERNAL)
        self.assertEqual(transaction.payout_method, Transaction.PAYOUT_BANK)
        self.assertEqual(transaction.network, "Bitcoin")
        self.assertEqual(transaction.bank_name, beneficiary.bank_name)
        self.assertEqual(transaction.bank_account_name, beneficiary.account_name)
        self.assertEqual(transaction.bank_account_number, beneficiary.account_number)
        self.assertEqual(transaction.bank_account_type, beneficiary.account_type)
        self.assertEqual(transaction.broker_wallet_address, "bc1qquidaxwallet123")
        self.assertTrue(QuidaxDeposit.objects.filter(broker_transaction=transaction, status=QuidaxDeposit.PENDING).exists())
        wallet = WalletBalance.objects.filter(user=self.user, asset=self.asset).first()
        if wallet:
            self.assertEqual(wallet.balance, Decimal("0E-8"))
            self.assertEqual(wallet.locked_balance, Decimal("0E-8"))

    def test_create_sell_transaction_ignores_cheeseball_wallet_source_and_does_not_lock_crypto(self):
        beneficiary = BeneficiaryBankAccount.objects.create(
            user=self.user,
            account_name="Jane Doe",
            bank_name="Demo Bank",
            account_number="0123456789",
            account_type=BeneficiaryBankAccount.SAVINGS,
        )


        WalletBalance.objects.update_or_create(user=self.user, asset=self.asset, defaults={"balance": self.sell_quote.crypto_amount})

        transaction = create_sell_transaction(
            self.make_request(self.user),
            SimpleNamespace(
                quote_id=self.sell_quote.id,
                crypto_source=Transaction.CRYPTO_SOURCE_CHEESEBALL,
                payout_method=Transaction.PAYOUT_BANK,
                beneficiary_id=beneficiary.id,
            ),
        )

        wallet = WalletBalance.objects.get(user=self.user, asset=self.asset)
        self.assertIsInstance(transaction, Transaction)
        self.assertEqual(transaction.transaction_type, Transaction.SELL)
        self.assertEqual(transaction.crypto_source, Transaction.CRYPTO_SOURCE_EXTERNAL)
        self.assertEqual(wallet.balance, self.sell_quote.crypto_amount)
        self.assertEqual(wallet.locked_balance, Decimal("0E-8"))
        self.assertFalse(WalletLedger.objects.filter(transaction_type=WalletLedger.CONVERSION_LOCK, reference_id=transaction.id).exists())

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
            SimpleNamespace(
                quote_id=self.sell_quote.id,
                payout_method=Transaction.PAYOUT_BANK,
                beneficiary_id=beneficiary.id,
            ),
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            json.loads(response.content)["detail"],
            "['Beneficiary bank account not found']",
        )

    def test_external_sell_to_ngn_wallet_credits_ngn_on_completion(self):
        transaction = create_sell_transaction(
            self.make_request(self.user),
            SimpleNamespace(
                quote_id=self.sell_quote.id,
                payout_method=Transaction.PAYOUT_NGN_WALLET,
                beneficiary_id=None,
                network="Bitcoin",
            ),
        )
        PlatformReserve.objects.update_or_create(asset=self.asset, defaults={"balance": Decimal("0.00000000")})

        transition_transaction(transaction, Transaction.PENDING_REVIEW)
        approve_transaction(self.make_request(self.admin), transaction.id, SimpleNamespace(note="Crypto received"))
        complete_transaction(self.make_request(self.admin), transaction.id, SimpleNamespace(note="Paid to wallet"))

        ngn_wallet = WalletBalance.objects.get(user=self.user, asset=self.ngn_asset)
        transaction.refresh_from_db()
        self.assertEqual(transaction.status, Transaction.COMPLETED)
        self.assertEqual(ngn_wallet.balance, self.sell_quote.naira_amount)
        self.assertEqual(PlatformReserve.objects.get(asset=self.asset).balance, self.sell_quote.crypto_amount)

    def test_external_sell_to_bank_does_not_credit_ngn_wallet_on_completion(self):
        beneficiary = self.create_beneficiary()
        transaction = create_sell_transaction(
            self.make_request(self.user),
            SimpleNamespace(
                quote_id=self.sell_quote.id,
                payout_method=Transaction.PAYOUT_BANK,
                beneficiary_id=beneficiary.id,
            ),
        )
        PlatformReserve.objects.update_or_create(asset=self.asset, defaults={"balance": Decimal("0.00000000")})

        transition_transaction(transaction, Transaction.PENDING_REVIEW)
        approve_transaction(self.make_request(self.admin), transaction.id, SimpleNamespace(note="Crypto received"))
        complete_transaction(self.make_request(self.admin), transaction.id, SimpleNamespace(note="Bank paid"))

        transaction.refresh_from_db()
        self.assertEqual(transaction.status, Transaction.COMPLETED)
        self.assertFalse(WalletBalance.objects.filter(user=self.user, asset=self.ngn_asset).exists())
        self.assertEqual(PlatformReserve.objects.get(asset=self.asset).balance, self.sell_quote.crypto_amount)

    def test_double_finalize_raises(self):

        pr, _ = PlatformReserve.objects.update_or_create(asset=self.asset, defaults={"balance": self.buy_quote.crypto_amount})


        self.buy_transaction.status = Transaction.PAID
        self.buy_transaction.save(update_fields=["status"])


        transition_transaction(self.buy_transaction, Transaction.COMPLETED, admin_user=self.admin, note="complete")
        self.buy_transaction.refresh_from_db()
        self.assertTrue(self.buy_transaction.finalized)


        reserve_count = ReserveMovement.objects.filter(asset=self.asset).count()
        ledger_count = WalletLedger.objects.filter(user=self.user).count()
        wallet_balance_before = WalletBalance.objects.get(user=self.user, asset=self.asset).balance


        with self.assertRaises(ValueError):
            _finalize_transaction(self.buy_transaction)

        self.assertEqual(ReserveMovement.objects.filter(asset=self.asset).count(), reserve_count)
        self.assertEqual(WalletLedger.objects.filter(user=self.user).count(), ledger_count)
        self.assertEqual(WalletBalance.objects.get(user=self.user, asset=self.asset).balance, wallet_balance_before)
