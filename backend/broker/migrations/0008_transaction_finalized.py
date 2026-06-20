

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('broker', '0007_extract_payouts_and_wallets'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='finalized',
            field=models.BooleanField(default=False),
        ),
    ]
