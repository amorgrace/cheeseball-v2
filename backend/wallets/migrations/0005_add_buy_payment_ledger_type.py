from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("wallets", "0004_alter_platformaccount_platform_address"),
    ]

    operations = [
        migrations.AlterField(
            model_name="ledger",
            name="transaction_type",
            field=models.CharField(
                choices=[
                    ("wallet_deposit", "Wallet Deposit"),
                    ("wallet_withdrawal", "Wallet Withdrawal"),
                    ("buy_payment", "Buy Payment"),
                    ("conversion_debit", "Conversion Debit"),
                    ("conversion_credit", "Conversion Credit"),
                    ("withdrawal_lock", "Withdrawal Lock"),
                    ("withdrawal_release", "Withdrawal Release"),
                    ("withdrawal_debit", "Withdrawal Debit"),
                    ("conversion_lock", "Conversion Lock"),
                    ("sell_lock_released", "Sell Lock Released"),
                    ("conversion_release", "Conversion Release"),
                ],
                max_length=30,
            ),
        ),
    ]
