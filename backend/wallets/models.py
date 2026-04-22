import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class WalletBalance(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wallet_balances")
    asset = models.ForeignKey("rates.Asset", on_delete=models.CASCADE, related_name="wallet_balances", to_field="code", db_column="asset")
    balance = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    locked_balance = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "asset")
        ordering = ["-updated_at"]
        db_table = "broker_walletbalance"

    def __str__(self):
        return f"{self.user.email} - {self.asset.code}: {self.balance}"

    @property
    def available_balance(self):
        return self.balance - self.locked_balance


class RateLock(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="rate_locks")
    from_asset = models.ForeignKey("rates.Asset", on_delete=models.CASCADE, related_name="rate_locks_from", to_field="code", db_column="from_asset")
    to_asset = models.ForeignKey("rates.Asset", on_delete=models.CASCADE, related_name="rate_locks_to", to_field="code", db_column="to_asset")
    from_amount = models.DecimalField(max_digits=20, decimal_places=8)
    to_amount = models.DecimalField(max_digits=20, decimal_places=8)
    rate = models.DecimalField(max_digits=20, decimal_places=8)
    markup_percent = models.DecimalField(max_digits=6, decimal_places=2)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        db_table = "broker_ratelock"

    def __str__(self):
        return f"{self.user.email} - {self.from_asset.code}/{self.to_asset.code}"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at


class Conversion(models.Model):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    STATUS_CHOICES = (
        (PENDING, "Pending"),
        (COMPLETED, "Completed"),
        (FAILED, "Failed"),
        (CANCELLED, "Cancelled"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversions")
    rate_lock = models.ForeignKey("wallets.RateLock", on_delete=models.SET_NULL, null=True, blank=True, related_name="conversions")
    from_asset = models.ForeignKey("rates.Asset", on_delete=models.PROTECT, related_name="conversions_from", to_field="code", db_column="from_asset")
    to_asset = models.ForeignKey("rates.Asset", on_delete=models.PROTECT, related_name="conversions_to", to_field="code", db_column="to_asset")
    from_amount = models.DecimalField(max_digits=20, decimal_places=8)
    to_amount = models.DecimalField(max_digits=20, decimal_places=8)
    rate = models.DecimalField(max_digits=20, decimal_places=8)
    markup_percent = models.DecimalField(max_digits=6, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        db_table = "broker_conversion"

    def __str__(self):
        return f"{self.user.email} - {self.from_asset.code} to {self.to_asset.code}"


class Withdrawal(models.Model):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    STATUS_CHOICES = (
        (PENDING, "Pending"),
        (COMPLETED, "Completed"),
        (FAILED, "Failed"),
        (CANCELLED, "Cancelled"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="withdrawals")
    asset = models.ForeignKey("rates.Asset", on_delete=models.PROTECT, related_name="withdrawals", to_field="code", db_column="asset")
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    bank_name = models.CharField(max_length=120, blank=True)
    bank_account_name = models.CharField(max_length=120, blank=True)
    bank_account_number = models.CharField(max_length=30, blank=True)
    wallet_address = models.CharField(max_length=255, blank=True)
    network = models.CharField(max_length=50, blank=True)
    admin_notes = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_withdrawals")
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        db_table = "broker_withdrawal"

    def __str__(self):
        return f"{self.user.email} - {self.asset.code} {self.amount}"


class Ledger(models.Model):
    WALLET_DEPOSIT = "wallet_deposit"
    WALLET_WITHDRAWAL = "wallet_withdrawal"
    CONVERSION_DEBIT = "conversion_debit"
    CONVERSION_CREDIT = "conversion_credit"
    WITHDRAWAL_LOCK = "withdrawal_lock"
    WITHDRAWAL_RELEASE = "withdrawal_release"
    WITHDRAWAL_DEBIT = "withdrawal_debit"
    CONVERSION_LOCK = "conversion_lock"
    CONVERSION_RELEASE = "conversion_release"
    TRANSACTION_TYPE_CHOICES = (
        (WALLET_DEPOSIT, "Wallet Deposit"),
        (WALLET_WITHDRAWAL, "Wallet Withdrawal"),
        (CONVERSION_DEBIT, "Conversion Debit"),
        (CONVERSION_CREDIT, "Conversion Credit"),
        (WITHDRAWAL_LOCK, "Withdrawal Lock"),
        (WITHDRAWAL_RELEASE, "Withdrawal Release"),
        (WITHDRAWAL_DEBIT, "Withdrawal Debit"),
        (CONVERSION_LOCK, "Conversion Lock"),
        (CONVERSION_RELEASE, "Conversion Release"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ledger_entries")
    wallet_balance = models.ForeignKey("wallets.WalletBalance", on_delete=models.CASCADE, related_name="ledger_entries")
    transaction_type = models.CharField(max_length=30, choices=TRANSACTION_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    balance_before = models.DecimalField(max_digits=20, decimal_places=8)
    balance_after = models.DecimalField(max_digits=20, decimal_places=8)
    locked_before = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    locked_after = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    reference_id = models.UUIDField(null=True, blank=True)
    reference_model = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["wallet_balance", "-created_at"]),
        ]
        db_table = "broker_ledger"

    def __str__(self):
        return f"{self.user.email} - {self.transaction_type}: {self.amount}"

