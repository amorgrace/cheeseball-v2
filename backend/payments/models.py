import uuid

from django.db import models


class PaymentRecord(models.Model):
    PENDING = "pending"
    PENDING_REVIEW = "pending_review"
    VERIFIED = "verified"
    FAILED = "failed"
    STATUS_CHOICES = (
        (PENDING, "Pending"),
        (PENDING_REVIEW, "Pending review"),
        (VERIFIED, "Verified"),
        (FAILED, "Failed"),
    )

    PAYSTACK = "paystack"
    BANK_TRANSFER = "bank_transfer"
    NGN_WALLET = "ngn_wallet"
    METHOD_CHOICES = (
        (PAYSTACK, "Paystack"),
        (BANK_TRANSFER, "Bank transfer"),
        (NGN_WALLET, "NGN wallet"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaction = models.OneToOneField("broker.Transaction", on_delete=models.CASCADE, related_name="payment_record")
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    provider = models.CharField(max_length=30, blank=True)
    provider_reference = models.CharField(max_length=120, blank=True)
    receipt_reference = models.CharField(max_length=255, blank=True)
    receipt_url = models.URLField(blank=True)
    receipt_note = models.TextField(blank=True)
    provider_payload = models.JSONField(default=dict, blank=True)
    user_confirmed_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.method} payment for {self.transaction_id}"
