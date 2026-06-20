

from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='RateConfiguration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('asset', models.CharField(default='BTC', max_length=10, unique=True)),
                ('buy_markup_percent', models.DecimalField(decimal_places=2, default=Decimal('3.00'), max_digits=6)),
                ('sell_markup_percent', models.DecimalField(decimal_places=2, default=Decimal('2.00'), max_digits=6)),
                ('fallback_market_rate', models.DecimalField(decimal_places=2, default=Decimal('150000000.00'), max_digits=20)),
                ('is_active', models.BooleanField(default=True)),
                ('last_market_rate', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('last_synced_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['asset'],
            },
        ),
        migrations.CreateModel(
            name='RateQuote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('asset', models.CharField(default='BTC', max_length=10)),
                ('quote_type', models.CharField(choices=[('buy', 'Buy'), ('sell', 'Sell')], max_length=10)),
                ('market_rate', models.DecimalField(decimal_places=2, max_digits=20)),
                ('markup_percent', models.DecimalField(decimal_places=2, max_digits=6)),
                ('final_rate', models.DecimalField(decimal_places=2, max_digits=20)),
                ('naira_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('crypto_amount', models.DecimalField(blank=True, decimal_places=8, max_digits=20, null=True)),
                ('source', models.CharField(default='fallback', max_length=30)),
                ('expires_at', models.DateTimeField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
