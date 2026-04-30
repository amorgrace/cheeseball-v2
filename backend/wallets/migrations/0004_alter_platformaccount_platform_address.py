from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wallets', '0003_remove_etc_platformreserve_and_walletbalances'),
    ]

    operations = [
        migrations.AlterField(
            model_name='platformaccount',
            name='platform_address',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
