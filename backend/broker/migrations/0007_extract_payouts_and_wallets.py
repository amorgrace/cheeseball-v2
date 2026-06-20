from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("broker", "0006_beneficiarybankaccount_transaction_bank_account_type"),
        ("payouts", "0001_initial"),
        ("wallets", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.DeleteModel(name="BeneficiaryBankAccount"),
                migrations.DeleteModel(name="Conversion"),
                migrations.DeleteModel(name="Ledger"),
                migrations.DeleteModel(name="RateLock"),
                migrations.DeleteModel(name="WalletBalance"),
                migrations.DeleteModel(name="Withdrawal"),
            ],
        ),
    ]
