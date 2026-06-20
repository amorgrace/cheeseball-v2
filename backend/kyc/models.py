import uuid

from django.conf import settings
from django.db import models


class KYCSubmission(models.Model):
    SUBMITTED = "submitted"
    VERIFIED = "verified"
    REJECTED = "rejected"
    STATUS_CHOICES = (
        (SUBMITTED, "Submitted"),
        (VERIFIED, "Verified"),
        (REJECTED, "Rejected"),
    )

    ID_TYPE_CHOICES = (
        ("nin", "NIN"),
        ("passport", "Passport"),
        ("drivers_license", "Driver's license"),
        ("voters_card", "Voter's card"),
        ("other", "Other"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="kyc_submissions")
    id_type = models.CharField(max_length=50, choices=ID_TYPE_CHOICES)
    document_url = models.URLField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=SUBMITTED)
    admin_note = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_kyc_submissions",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} - {self.status}"

