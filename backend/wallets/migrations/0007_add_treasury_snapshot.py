from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("wallets", "0006_walletfunding"),
        ("rates", "0008_asset_transfer_flags"),
    ]

    operations = [
        migrations.CreateModel(
            name="TreasurySnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "asset",
                    models.ForeignKey(
                        db_column="asset",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="treasury_snapshots",
                        to="rates.asset",
                        to_field="code",
                    ),
                ),
                ("balance", models.DecimalField(decimal_places=8, default=0, max_digits=30)),
                ("source", models.CharField(default="quidax", max_length=30)),
                ("synced_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["-synced_at"],
                "db_table": "broker_treasurysnapshot",
                "indexes": [
                    models.Index(fields=["asset", "-synced_at"], name="broker_tres_asset_synced_idx"),
                ],
            },
        ),
    ]
