import uuid

from django.conf import settings
from django.db import models


class Notification(models.Model):
    # Notification types
    TRANSACTION_COMPLETED = "transaction_completed"
    TRANSACTION_FAILED = "transaction_failed"
    TRANSACTION_REJECTED = "transaction_rejected"
    DEPOSIT_RECEIVED = "deposit_received"
    WITHDRAWAL_APPROVED = "withdrawal_approved"
    WITHDRAWAL_REJECTED = "withdrawal_rejected"
    KYC_APPROVED = "kyc_approved"
    KYC_REJECTED = "kyc_rejected"
    REFERRAL_REWARD = "referral_reward"
    CRYPTO_SENT = "crypto_sent"
    CRYPTO_RECEIVED = "crypto_received"
    GENERAL = "general"

    TYPE_CHOICES = (
        (TRANSACTION_COMPLETED, "Transaction Completed"),
        (TRANSACTION_FAILED, "Transaction Failed"),
        (TRANSACTION_REJECTED, "Transaction Rejected"),
        (DEPOSIT_RECEIVED, "Deposit Received"),
        (WITHDRAWAL_APPROVED, "Withdrawal Approved"),
        (WITHDRAWAL_REJECTED, "Withdrawal Rejected"),
        (KYC_APPROVED, "KYC Approved"),
        (KYC_REJECTED, "KYC Rejected"),
        (REFERRAL_REWARD, "Referral Reward"),
        (CRYPTO_SENT, "Crypto Sent"),
        (CRYPTO_RECEIVED, "Crypto Received"),
        (GENERAL, "General"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    type = models.CharField(max_length=30, choices=TYPE_CHOICES, default=GENERAL)
    is_read = models.BooleanField(default=False)
    reference_id = models.UUIDField(null=True, blank=True)
    reference_type = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["user", "is_read"]),
        ]

    def __str__(self):
        return f"{self.user.email} — {self.title}"
