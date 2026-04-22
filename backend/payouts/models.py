import uuid

from django.conf import settings
from django.db import models


class BeneficiaryBankAccount(models.Model):
    SAVINGS = "savings"
    CHECKING = "checking"
    ACCOUNT_TYPE_CHOICES = (
        (SAVINGS, "Savings"),
        (CHECKING, "Checking"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="beneficiary_bank_accounts")
    account_name = models.CharField(max_length=120)
    bank_name = models.CharField(max_length=120)
    account_number = models.CharField(max_length=30)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["account_name", "bank_name", "account_number"]
        unique_together = ("user", "bank_name", "account_number")
        db_table = "broker_beneficiarybankaccount"

    def __str__(self):
        return f"{self.user.email} - {self.account_name} ({self.bank_name})"

