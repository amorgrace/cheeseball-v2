import uuid

from django.conf import settings
from django.db import models


class QuidaxSubAccount(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="quidax_sub_account")
    quidax_id = models.CharField(max_length=128, unique=True)
    email = models.EmailField(blank=True)
    provider_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} - Quidax {self.quidax_id}"


class QuidaxWalletAddress(models.Model):
    PENDING = "pending"
    GENERATED = "generated"
    FAILED = "failed"
    STATUS_CHOICES = (
        (PENDING, "Pending"),
        (GENERATED, "Generated"),
        (FAILED, "Failed"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="quidax_wallet_addresses")
    sub_account = models.ForeignKey(QuidaxSubAccount, on_delete=models.CASCADE, related_name="wallet_addresses")
    currency = models.CharField(max_length=20)
    network = models.CharField(max_length=50, blank=True)
    address = models.CharField(max_length=255, blank=True)
    destination_tag = models.CharField(max_length=128, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    provider_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "currency", "network")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} - {self.currency}/{self.network or '-'}"


class QuidaxDeposit(models.Model):
    PENDING = "pending"
    SUCCESSFUL = "successful"
    FAILED = "failed"
    STATUS_CHOICES = (
        (PENDING, "Pending"),
        (SUCCESSFUL, "Successful"),
        (FAILED, "Failed"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="quidax_deposits")
    sub_account = models.ForeignKey(QuidaxSubAccount, on_delete=models.SET_NULL, null=True, blank=True, related_name="deposits")
    wallet_address = models.ForeignKey(QuidaxWalletAddress, on_delete=models.SET_NULL, null=True, blank=True, related_name="deposits")
    broker_transaction = models.OneToOneField("broker.Transaction", on_delete=models.SET_NULL, null=True, blank=True, related_name="quidax_deposit")
    currency = models.CharField(max_length=20)
    network = models.CharField(max_length=50, blank=True)
    amount = models.DecimalField(max_digits=30, decimal_places=8)
    txid = models.CharField(max_length=255, blank=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    provider_reference = models.CharField(max_length=128, blank=True, db_index=True)
    provider_payload = models.JSONField(default=dict, blank=True)
    credited_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "currency", "status"]),
            models.Index(fields=["txid", "currency"]),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.amount} {self.currency} ({self.status})"


class QuidaxWithdrawal(models.Model):
    PENDING = "pending"
    SUCCESSFUL = "successful"
    REJECTED = "rejected"
    STATUS_CHOICES = (
        (PENDING, "Pending"),
        (SUCCESSFUL, "Successful"),
        (REJECTED, "Rejected"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="quidax_withdrawals")
    currency = models.CharField(max_length=20)
    network = models.CharField(max_length=50, blank=True)
    amount = models.DecimalField(max_digits=30, decimal_places=8)
    address = models.CharField(max_length=255)
    reference = models.CharField(max_length=128, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    provider_payload = models.JSONField(default=dict, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} - withdraw {self.amount} {self.currency}"


class QuidaxWebhookEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=80)
    provider_event_id = models.CharField(max_length=255, unique=True)
    signature = models.CharField(max_length=255, blank=True)
    payload = models.JSONField(default=dict)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.event_type} - {self.provider_event_id}"
