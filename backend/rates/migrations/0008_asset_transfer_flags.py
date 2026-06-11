from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rates", "0007_seed_usdc_asset"),
    ]

    operations = [
        migrations.AddField(
            model_name="asset",
            name="deposit_enabled",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="asset",
            name="send_enabled",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="asset",
            name="withdrawal_mode",
            field=models.CharField(
                choices=[("auto", "Automatic"), ("manual", "Manual Review")],
                default="auto",
                max_length=10,
            ),
        ),
    ]
