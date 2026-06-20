from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("broker", "0008_transaction_finalized"),
    ]

    operations = [
        migrations.AlterField(
            model_name="transaction",
            name="payment_method",
            field=models.CharField(
                blank=True,
                choices=[
                    ("paystack", "Paystack"),
                    ("bank_transfer", "Bank transfer"),
                    ("ngn_wallet", "NGN wallet"),
                ],
                max_length=20,
                null=True,
            ),
        ),
    ]
