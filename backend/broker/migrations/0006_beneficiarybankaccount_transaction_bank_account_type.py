

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("broker", "0005_ratelock_conversion_walletbalance_withdrawal_ledger"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="transaction",
            name="bank_account_type",
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.CreateModel(
            name="BeneficiaryBankAccount",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("account_name", models.CharField(max_length=120)),
                ("bank_name", models.CharField(max_length=120)),
                ("account_number", models.CharField(max_length=30)),
                ("account_type", models.CharField(choices=[("savings", "Savings"), ("checking", "Checking")], max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="beneficiary_bank_accounts", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["account_name", "bank_name", "account_number"],
                "unique_together": {("user", "bank_name", "account_number")},
            },
        ),
    ]
