from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rates", "0005_asset_network"),
    ]

    operations = [
        migrations.AddField(
            model_name="ratequote",
            name="crypto_usd_price",
            field=models.DecimalField(decimal_places=8, default=Decimal("0.00000000"), max_digits=20),
        ),
    ]
