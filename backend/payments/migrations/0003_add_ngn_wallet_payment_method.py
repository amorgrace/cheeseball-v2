from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0002_paymentrecord_receipt_url"),
    ]

    operations = [
        migrations.AlterField(
            model_name="paymentrecord",
            name="method",
            field=models.CharField(
                choices=[
                    ("paystack", "Paystack"),
                    ("bank_transfer", "Bank transfer"),
                    ("ngn_wallet", "NGN wallet"),
                ],
                max_length=20,
            ),
        ),
    ]
