import random
import string
import uuid

from django.conf import settings
from django.db import models


def generate_transaction_id():
    # 3 chars "tx-" + 13 chars random combo = 16 units max
    return "tx-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=13))

class Transaction(models.Model):
    BUY = "buy"
    SELL = "sell"
    TRANSACTION_TYPES = (
        (BUY, "Buy"),
        (SELL, "Sell"),
    )

    PENDING_PAYMENT = "pending_payment"
    PENDING_REVIEW = "pending_review"
    PAID = "paid"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"
    STATUS_CHOICES = (
        (PENDING_PAYMENT, "Pending payment"),
        (PENDING_REVIEW, "Pending review"),
        (PAID, "Paid"),
        (PROCESSING, "Processing"),
        (COMPLETED, "Completed"),
        (FAILED, "Failed"),
        (REJECTED, "Rejected"),
    )

    PAYSTACK = "paystack"
    BANK_TRANSFER = "bank_transfer"
    NGN_WALLET = "ngn_wallet"
    PAYMENT_METHOD_CHOICES = (
        (PAYSTACK, "Paystack"),
        (BANK_TRANSFER, "Bank transfer"),
        (NGN_WALLET, "NGN wallet"),
    )
    CRYPTO_SOURCE_CHEESEBALL = "cheeseball_wallet"
    CRYPTO_SOURCE_EXTERNAL = "external_wallet"
    CRYPTO_SOURCE_CHOICES = (
        (CRYPTO_SOURCE_CHEESEBALL, "CheeseBall wallet"),
        (CRYPTO_SOURCE_EXTERNAL, "External wallet"),
    )
    PAYOUT_NGN_WALLET = "ngn_wallet"
    PAYOUT_METHOD_CHOICES = (
        (PAYOUT_NGN_WALLET, "NGN wallet"),
    )

    id = models.CharField(max_length=20, primary_key=True, default=generate_transaction_id, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="transactions")
    quote = models.ForeignKey("rates.RateQuote", on_delete=models.SET_NULL, null=True, blank=True, related_name="transactions")
    custody_deposit = models.ForeignKey(
        "nowpayments.CustodyDeposit",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="broker_transactions",
    )
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    asset = models.ForeignKey(
        "rates.Asset",
        on_delete=models.PROTECT,
        related_name="transactions",
        to_field="code",
        db_column="asset",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING_PAYMENT)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, null=True, blank=True)
    naira_amount = models.DecimalField(max_digits=20, decimal_places=2)
    crypto_amount = models.DecimalField(max_digits=20, decimal_places=8)
    market_rate = models.DecimalField(max_digits=20, decimal_places=2)
    markup_percent = models.DecimalField(max_digits=6, decimal_places=2)
    final_rate = models.DecimalField(max_digits=20, decimal_places=2)
    crypto_usd_price = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    wallet_address = models.CharField(max_length=255, blank=True)
    network = models.CharField(max_length=50, blank=True)
    broker_wallet_address = models.CharField(max_length=255, blank=True)
    crypto_source = models.CharField(max_length=30, choices=CRYPTO_SOURCE_CHOICES, default=CRYPTO_SOURCE_EXTERNAL)
    payout_method = models.CharField(max_length=30, choices=PAYOUT_METHOD_CHOICES, blank=True)
    bank_name = models.CharField(max_length=120, blank=True)
    bank_account_name = models.CharField(max_length=120, blank=True)
    bank_account_number = models.CharField(max_length=30, blank=True)
    bank_account_type = models.CharField(max_length=20, blank=True)
    admin_notes = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_broker_transactions",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    finalized = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.transaction_type.upper()} {self.asset.code} {self.id}"

    @property
    def asset_code(self) -> str:
        return self.asset.code

    @property
    def asset_name(self) -> str:
        return self.asset.name
