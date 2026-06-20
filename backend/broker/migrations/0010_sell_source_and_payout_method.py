from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("broker", "0009_add_ngn_wallet_payment_method"),
    ]

    operations = [
        migrations.AddField(
            model_name="transaction",
            name="crypto_source",
            field=models.CharField(
                choices=[
                    ("cheeseball_wallet", "CheeseBall wallet"),
                    ("external_wallet", "External wallet"),
                ],
                default="external_wallet",
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="transaction",
            name="payout_method",
            field=models.CharField(
                blank=True,
                choices=[
                    ("beneficiary_bank", "Beneficiary bank"),
                    ("ngn_wallet", "NGN wallet"),
                ],
                max_length=30,
            ),
        ),
    ]
