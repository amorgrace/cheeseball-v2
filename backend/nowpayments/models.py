import uuid

from django.conf import settings
from django.db import models


class CustodyAccount(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="nowpayments_custody_account")
    sub_partner_id = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=30, unique=True)
    provider_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} - NOWPayments {self.sub_partner_id}"


class CustodyDeposit(models.Model):
    PENDING = "pending"
    FINISHED = "finished"
    FAILED = "failed"
    EXPIRED = "expired"
    STATUS_CHOICES = (
        (PENDING, "Pending"),
        (FINISHED, "Finished"),
        (FAILED, "Failed"),
        (EXPIRED, "Expired"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="nowpayments_custody_deposits")
    custody_account = models.ForeignKey(CustodyAccount, on_delete=models.CASCADE, related_name="deposits")
    currency = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=30, decimal_places=8)
    provider_payment_id = models.CharField(max_length=128, blank=True, db_index=True)
    pay_address = models.CharField(max_length=255, blank=True)
    pay_amount = models.DecimalField(max_digits=30, decimal_places=8, null=True, blank=True)
    payment_status = models.CharField(max_length=30, default=PENDING)
    provider_payload = models.JSONField(default=dict, blank=True)
    credited_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} - {self.amount} {self.currency} ({self.payment_status})"
