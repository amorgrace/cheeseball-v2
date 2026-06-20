from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("broker", "0010_sell_source_and_payout_method"),
    ]

    operations = [
        migrations.AddField(
            model_name="transaction",
            name="crypto_usd_price",
            field=models.DecimalField(decimal_places=8, default=Decimal("0.00000000"), max_digits=20),
        ),
    ]
