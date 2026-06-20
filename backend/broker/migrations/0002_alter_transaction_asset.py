

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('broker', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transaction',
            name='asset',
            field=models.CharField(choices=[('BTC', 'Bitcoin'), ('ETH', 'Ethereum'), ('USDT', 'Tether')], default='BTC', max_length=10),
        ),
    ]
