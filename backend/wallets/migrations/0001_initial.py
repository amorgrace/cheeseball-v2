import uuid

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("broker", "0006_beneficiarybankaccount_transaction_bank_account_type"),
        ("rates", "0004_asset_alter_rateconfiguration_options_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="WalletBalance",
                    fields=[
                        ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                        ("balance", models.DecimalField(decimal_places=8, default=0, max_digits=20)),
                        ("locked_balance", models.DecimalField(decimal_places=8, default=0, max_digits=20)),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                        ("updated_at", models.DateTimeField(auto_now=True)),
                        ("asset", models.ForeignKey(db_column="asset", on_delete=models.deletion.CASCADE, related_name="wallet_balances", to="rates.asset", to_field="code")),
                        ("user", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="wallet_balances", to=settings.AUTH_USER_MODEL)),
                    ],
                    options={
                        "ordering": ["-updated_at"],
                        "unique_together": {("user", "asset")},
                        "db_table": "broker_walletbalance",
                    },
                ),
                migrations.CreateModel(
                    name="RateLock",
                    fields=[
                        ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                        ("from_amount", models.DecimalField(decimal_places=8, max_digits=20)),
                        ("to_amount", models.DecimalField(decimal_places=8, max_digits=20)),
                        ("rate", models.DecimalField(decimal_places=8, max_digits=20)),
                        ("markup_percent", models.DecimalField(decimal_places=2, max_digits=6)),
                        ("expires_at", models.DateTimeField()),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                        ("from_asset", models.ForeignKey(db_column="from_asset", on_delete=models.deletion.CASCADE, related_name="rate_locks_from", to="rates.asset", to_field="code")),
                        ("to_asset", models.ForeignKey(db_column="to_asset", on_delete=models.deletion.CASCADE, related_name="rate_locks_to", to="rates.asset", to_field="code")),
                        ("user", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="rate_locks", to=settings.AUTH_USER_MODEL)),
                    ],
                    options={"ordering": ["-created_at"], "db_table": "broker_ratelock"},
                ),
                migrations.CreateModel(
                    name="Conversion",
                    fields=[
                        ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                        ("from_amount", models.DecimalField(decimal_places=8, max_digits=20)),
                        ("to_amount", models.DecimalField(decimal_places=8, max_digits=20)),
                        ("rate", models.DecimalField(decimal_places=8, max_digits=20)),
                        ("markup_percent", models.DecimalField(decimal_places=2, max_digits=6)),
                        ("status", models.CharField(choices=[("pending", "Pending"), ("completed", "Completed"), ("failed", "Failed"), ("cancelled", "Cancelled")], default="pending", max_length=20)),
                        ("completed_at", models.DateTimeField(blank=True, null=True)),
                        ("failed_at", models.DateTimeField(blank=True, null=True)),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                        ("updated_at", models.DateTimeField(auto_now=True)),
                        ("from_asset", models.ForeignKey(db_column="from_asset", on_delete=models.deletion.PROTECT, related_name="conversions_from", to="rates.asset", to_field="code")),
                        ("to_asset", models.ForeignKey(db_column="to_asset", on_delete=models.deletion.PROTECT, related_name="conversions_to", to="rates.asset", to_field="code")),
                        ("user", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="conversions", to=settings.AUTH_USER_MODEL)),
                        ("rate_lock", models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, related_name="conversions", to="wallets.ratelock")),
                    ],
                    options={"ordering": ["-created_at"], "db_table": "broker_conversion"},
                ),
                migrations.CreateModel(
                    name="Withdrawal",
                    fields=[
                        ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                        ("amount", models.DecimalField(decimal_places=8, max_digits=20)),
                        ("status", models.CharField(choices=[("pending", "Pending"), ("completed", "Completed"), ("failed", "Failed"), ("cancelled", "Cancelled")], default="pending", max_length=20)),
                        ("bank_name", models.CharField(blank=True, max_length=120)),
                        ("bank_account_name", models.CharField(blank=True, max_length=120)),
                        ("bank_account_number", models.CharField(blank=True, max_length=30)),
                        ("wallet_address", models.CharField(blank=True, max_length=255)),
                        ("network", models.CharField(blank=True, max_length=50)),
                        ("admin_notes", models.TextField(blank=True)),
                        ("rejection_reason", models.TextField(blank=True)),
                        ("completed_at", models.DateTimeField(blank=True, null=True)),
                        ("failed_at", models.DateTimeField(blank=True, null=True)),
                        ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                        ("updated_at", models.DateTimeField(auto_now=True)),
                        ("approved_by", models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, related_name="approved_withdrawals", to=settings.AUTH_USER_MODEL)),
                        ("asset", models.ForeignKey(db_column="asset", on_delete=models.deletion.PROTECT, related_name="withdrawals", to="rates.asset", to_field="code")),
                        ("user", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="withdrawals", to=settings.AUTH_USER_MODEL)),
                    ],
                    options={"ordering": ["-created_at"], "db_table": "broker_withdrawal"},
                ),
                migrations.CreateModel(
                    name="Ledger",
                    fields=[
                        ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                        ("transaction_type", models.CharField(choices=[("wallet_deposit", "Wallet Deposit"), ("wallet_withdrawal", "Wallet Withdrawal"), ("conversion_debit", "Conversion Debit"), ("conversion_credit", "Conversion Credit"), ("withdrawal_lock", "Withdrawal Lock"), ("withdrawal_release", "Withdrawal Release"), ("withdrawal_debit", "Withdrawal Debit"), ("conversion_lock", "Conversion Lock"), ("conversion_release", "Conversion Release")], max_length=30)),
                        ("amount", models.DecimalField(decimal_places=8, max_digits=20)),
                        ("balance_before", models.DecimalField(decimal_places=8, max_digits=20)),
                        ("balance_after", models.DecimalField(decimal_places=8, max_digits=20)),
                        ("locked_before", models.DecimalField(decimal_places=8, default=0, max_digits=20)),
                        ("locked_after", models.DecimalField(decimal_places=8, default=0, max_digits=20)),
                        ("reference_id", models.UUIDField(blank=True, null=True)),
                        ("reference_model", models.CharField(blank=True, max_length=50)),
                        ("notes", models.TextField(blank=True)),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                        ("user", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="ledger_entries", to=settings.AUTH_USER_MODEL)),
                        ("wallet_balance", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="ledger_entries", to="wallets.walletbalance")),
                    ],
                    options={
                        "ordering": ["-created_at"],
                        "db_table": "broker_ledger",
                        "indexes": [
                            models.Index(fields=["user", "-created_at"], name="broker_ledg_user_id_8274a3_idx"),
                            models.Index(fields=["wallet_balance", "-created_at"], name="broker_ledg_wallet__569355_idx"),
                        ],
                    },
                ),
            ],
        ),
    ]
