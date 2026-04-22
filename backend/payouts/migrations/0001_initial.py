import uuid

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("broker", "0006_beneficiarybankaccount_transaction_bank_account_type"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
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
                        ("user", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="beneficiary_bank_accounts", to=settings.AUTH_USER_MODEL)),
                    ],
                    options={
                        "ordering": ["account_name", "bank_name", "account_number"],
                        "unique_together": {("user", "bank_name", "account_number")},
                        "db_table": "broker_beneficiarybankaccount",
                    },
                ),
            ],
        ),
    ]
