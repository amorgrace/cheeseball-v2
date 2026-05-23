import hashlib
import hmac
import json
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.test import TestCase
from django.utils import timezone

from broker.models import Transaction
from payments.models import PaymentRecord
from payments.views import paystack_webhook, setup_payment, submit_bank_transfer, verify_bank_transfer
from rates.models import Asset, RateQuote


class PaymentFlowTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(email="buyer@example.com", password="secret123")
        self.admin = user_model.objects.create_user(
            email="admin@example.com",
            password="secret123",
            is_staff=True,
        )
        self.asset, _ = Asset.objects.get_or_create(
            code="BTC",
            defaults={"name": "Bitcoin", "is_active": True},
        )
        self.quote = RateQuote.objects.create(
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
        self.transaction = Transaction.objects.create(
            user=self.user,
            quote=self.quote,
            transaction_type=Transaction.BUY,
            asset=self.asset,
            status=Transaction.PENDING_PAYMENT,
            payment_method=Transaction.BANK_TRANSFER,
            naira_amount=self.quote.naira_amount,
            crypto_amount=self.quote.crypto_amount,
            market_rate=self.quote.market_rate,
            markup_percent=self.quote.markup_percent,
            final_rate=self.quote.final_rate,
            wallet_address="0xabc123",
            network="BTC",
        )

    def make_request(self, user):
        return SimpleNamespace(auth=user, body=b"")

    def test_setup_payment_rejects_method_mismatch(self):
        payload = SimpleNamespace(
            transaction_id=self.transaction.id,
            payment_method=PaymentRecord.PAYSTACK,
        )

        response = setup_payment(self.make_request(self.user), payload)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            json.loads(response.content)["detail"],
            "Payment method does not match this transaction",
        )

    def test_setup_payment_for_ngn_wallet_returns_verified_record(self):
        self.transaction.payment_method = Transaction.NGN_WALLET
        self.transaction.status = Transaction.PAID
        self.transaction.paid_at = timezone.now()
        self.transaction.save(update_fields=["payment_method", "status", "paid_at"])

        payment_record = setup_payment(
            self.make_request(self.user),
            SimpleNamespace(
                transaction_id=self.transaction.id,
                payment_method=PaymentRecord.NGN_WALLET,
            ),
        )

        self.assertEqual(payment_record.method, PaymentRecord.NGN_WALLET)
        self.assertEqual(payment_record.provider, "wallet")
        self.assertEqual(payment_record.status, PaymentRecord.VERIFIED)

    @override_settings(PAYSTACK_SECRET_KEY="sk_test_demo", PAYSTACK_WEBHOOK_SECRET="sk_test_demo")
    @patch("payments.views.urlopen")
    def test_setup_payment_for_paystack_creates_bank_transfer_charge(self, mock_urlopen):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                return False

            def read(self):
                return json.dumps(
                    {
                        "status": True,
                        "message": "Charge attempted",
                        "data": {
                            "reference": "cb-demo",
                            "status": "pending",
                            "display_text": "Please transfer to the generated account",
                        },
                    }
                ).encode("utf-8")

        self.transaction.payment_method = Transaction.PAYSTACK
        self.transaction.save(update_fields=["payment_method"])
        mock_urlopen.return_value = FakeResponse()

        payment_record = setup_payment(
            self.make_request(self.user),
            SimpleNamespace(
                transaction_id=self.transaction.id,
                payment_method=PaymentRecord.PAYSTACK,
            ),
        )

        self.assertEqual(payment_record.method, PaymentRecord.PAYSTACK)
        self.assertEqual(payment_record.provider, "paystack")
        self.assertEqual(payment_record.status, PaymentRecord.PENDING)
        self.assertTrue(payment_record.provider_reference.startswith("cb-"))
        self.assertEqual(payment_record.provider_payload["data"]["status"], "pending")
        request = mock_urlopen.call_args.args[0]
        body = json.loads(request.data.decode("utf-8"))
        self.assertEqual(body["amount"], "10300000")
        self.assertEqual(body["currency"], "NGN")
        self.assertEqual(body["bank_transfer"].keys(), {"account_expires_at"})

    def test_submit_bank_transfer_stores_receipt_url_and_marks_pending_review(self):
        payload = SimpleNamespace(
            receipt_reference="TRX-12345",
            receipt_url="https://res.cloudinary.com/demo/image/upload/v1/receipt.png",
            receipt_note="Paid from mobile app",
        )

        payment_record = submit_bank_transfer(self.make_request(self.user), self.transaction.id, payload)

        self.transaction.refresh_from_db()
        self.assertEqual(payment_record.receipt_url, payload.receipt_url)
        self.assertEqual(payment_record.status, PaymentRecord.PENDING_REVIEW)
        self.assertEqual(self.transaction.status, Transaction.PENDING_REVIEW)

    def test_verify_bank_transfer_requires_pending_review(self):
        response = verify_bank_transfer(self.make_request(self.admin), self.transaction.id)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            json.loads(response.content)["detail"],
            "Only transactions pending review can be verified",
        )

    def test_verify_bank_transfer_marks_transaction_paid(self):
        submit_bank_transfer(
            self.make_request(self.user),
            self.transaction.id,
            SimpleNamespace(
                receipt_reference="TRX-12345",
                receipt_url="https://res.cloudinary.com/demo/image/upload/v1/receipt.png",
                receipt_note="Paid from mobile app",
            ),
        )

        payment_record = verify_bank_transfer(self.make_request(self.admin), self.transaction.id)

        self.transaction.refresh_from_db()
        self.assertEqual(payment_record.status, PaymentRecord.VERIFIED)
        self.assertEqual(self.transaction.status, Transaction.PAID)

    @override_settings(PAYSTACK_WEBHOOK_SECRET="sk_test_demo", PAYSTACK_CURRENCY="NGN")
    def test_paystack_webhook_verifies_payment_and_marks_transaction_paid(self):
        self.transaction.payment_method = Transaction.PAYSTACK
        self.transaction.save(update_fields=["payment_method"])
        payment_record = PaymentRecord.objects.create(
            transaction=self.transaction,
            method=PaymentRecord.PAYSTACK,
            provider="paystack",
            provider_reference="cb-demo-reference",
        )
        webhook_body = json.dumps(
            {
                "event": "charge.success",
                "data": {
                    "reference": payment_record.provider_reference,
                    "status": "success",
                    "amount": 10300000,
                    "currency": "NGN",
                    "channel": "bank_transfer",
                },
            }
        ).encode("utf-8")
        signature = hmac.new(b"sk_test_demo", webhook_body, hashlib.sha512).hexdigest()

        response = paystack_webhook(
            SimpleNamespace(body=webhook_body),
            SimpleNamespace(
                event="charge.success",
                data={
                    "reference": payment_record.provider_reference,
                    "status": "success",
                    "amount": 10300000,
                    "currency": "NGN",
                    "channel": "bank_transfer",
                },
            ),
            signature,
        )

        payment_record.refresh_from_db()
        self.transaction.refresh_from_db()
        self.assertEqual(response["message"], "Webhook processed")
        self.assertEqual(payment_record.status, PaymentRecord.VERIFIED)
        self.assertEqual(self.transaction.status, Transaction.PAID)

    @override_settings(PAYSTACK_WEBHOOK_SECRET="sk_test_demo", PAYSTACK_CURRENCY="NGN")
    def test_paystack_webhook_rejects_invalid_signature(self):
        response = paystack_webhook(
            SimpleNamespace(body=b"{}"),
            SimpleNamespace(event="charge.success", data={}),
            "bad-signature",
        )

        self.assertEqual(response.status_code, 401)
