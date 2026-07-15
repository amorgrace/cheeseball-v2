import uuid

from django.db import models


class TatumAddressSubscription(models.Model):
    """
    Tracks a Tatum address monitoring subscription.
    One subscription per HD wallet address — created when a deposit address is
    issued to a user.
    """

    ACTIVE = "active"
    CANCELLED = "cancelled"
    FAILED = "failed"
    STATUS_CHOICES = (
        (ACTIVE, "Active"),
        (CANCELLED, "Cancelled"),
        (FAILED, "Failed"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hd_address = models.OneToOneField(
        "hd_wallets.HdWalletAddress",
        on_delete=models.CASCADE,
        related_name="tatum_subscription",
    )
    tatum_subscription_id = models.CharField(max_length=255, unique=True, db_index=True)
    address = models.CharField(max_length=255, db_index=True)
    chain = models.CharField(max_length=50)
    subscription_type = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=ACTIVE)
    provider_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.chain}] {self.address[:16]}… → {self.tatum_subscription_id} ({self.status})"


class TatumWebhookEvent(models.Model):
    """
    Idempotency log for Tatum webhook notifications.
    Every incoming webhook is stored here before processing.
    Duplicate events (same tatum_event_id) are rejected via unique constraint.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tatum_event_id = models.CharField(max_length=255, unique=True, db_index=True)
    event_type = models.CharField(max_length=100, blank=True)
    address = models.CharField(max_length=255, blank=True, db_index=True)
    chain = models.CharField(max_length=50, blank=True)
    signature = models.CharField(max_length=512, blank=True)
    payload = models.JSONField(default=dict)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.event_type} — {self.tatum_event_id}"
