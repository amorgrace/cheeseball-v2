import uuid

from django.conf import settings
from django.db import models


class CryptoTransfer(models.Model):
    # Transfer type
    INTERNAL = "internal"  # user-to-user, in-app
    EXTERNAL = "external"  # on-chain to external wallet

    TRANSFER_TYPE_CHOICES = (
        (INTERNAL, "Internal (Cheeseball User)"),
        (EXTERNAL, "External (On-Chain)"),
    )

    # Status
    PENDING = "pending"
    PENDING_REVIEW = "pending_review"  # external send failed liquidity check, awaiting admin
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    STATUS_CHOICES = (
        (PENDING, "Pending"),
        (PENDING_REVIEW, "Pending Review"),
        (COMPLETED, "Completed"),
        (FAILED, "Failed"),
        (CANCELLED, "Cancelled"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_transfers",
    )
    # Recipient — populated for internal transfers; null for external
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="received_transfers",
    )
    # External destination — populated for external transfers; blank for internal
    recipient_address = models.CharField(max_length=255, blank=True)
    recipient_network = models.CharField(max_length=50, blank=True)

    asset = models.ForeignKey(
        "rates.Asset",
        on_delete=models.PROTECT,
        related_name="transfers",
        to_field="code",
        db_column="asset",
    )
    amount = models.DecimalField(max_digits=30, decimal_places=8)
    transfer_type = models.CharField(max_length=10, choices=TRANSFER_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)

    # Admin fields
    failure_reason = models.TextField(blank=True)
    admin_notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_transfers",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["sender", "-created_at"]),
            models.Index(fields=["recipient", "-created_at"]),
            models.Index(fields=["status", "-created_at"]),
        ]

    def __str__(self):
        if self.transfer_type == self.INTERNAL:
            dest = self.recipient.email if self.recipient else "unknown"
        else:
            dest = self.recipient_address or "unknown"
        return f"{self.sender.email} → {dest} | {self.amount} {self.asset_id} [{self.status}]"
