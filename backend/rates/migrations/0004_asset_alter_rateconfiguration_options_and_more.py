

import django.db.models.deletion
from django.db import migrations, models

ASSET_SEED_DATA = [
    {"code": "BTC", "name": "Bitcoin", "binance_symbol": "BTCUSDT", "fallback_market_rate": "150000000", "sort_order": 10},
    {"code": "ETH", "name": "Ethereum", "binance_symbol": "ETHUSDT", "fallback_market_rate": "5000000", "sort_order": 20},
    {"code": "USDT", "name": "Tether", "binance_symbol": "USDTUSDT", "fallback_market_rate": "1600", "sort_order": 30},
    {"code": "BNB", "name": "BNB", "binance_symbol": "BNBUSDT", "fallback_market_rate": "900000", "sort_order": 40},
    {"code": "SOL", "name": "Solana", "binance_symbol": "SOLUSDT", "fallback_market_rate": "240000", "sort_order": 50},
    {"code": "XRP", "name": "XRP", "binance_symbol": "XRPUSDT", "fallback_market_rate": "3500", "sort_order": 60},
    {"code": "TRX", "name": "TRON", "binance_symbol": "TRXUSDT", "fallback_market_rate": "220", "sort_order": 70},
    {"code": "LTC", "name": "Litecoin", "binance_symbol": "LTCUSDT", "fallback_market_rate": "140000", "sort_order": 80},
    {"code": "DOGE", "name": "Dogecoin", "binance_symbol": "DOGEUSDT", "fallback_market_rate": "280", "sort_order": 90},
    {"code": "BCH", "name": "Bitcoin Cash", "binance_symbol": "BCHUSDT", "fallback_market_rate": "800000", "sort_order": 100},
    {"code": "ADA", "name": "Cardano", "binance_symbol": "ADAUSDT", "fallback_market_rate": "1200", "sort_order": 110},
    {"code": "MATIC", "name": "Polygon", "binance_symbol": "MATICUSDT", "fallback_market_rate": "700", "sort_order": 120},
    {"code": "DOT", "name": "Polkadot", "binance_symbol": "DOTUSDT", "fallback_market_rate": "9000", "sort_order": 130},
    {"code": "LINK", "name": "Chainlink", "binance_symbol": "LINKUSDT", "fallback_market_rate": "25000", "sort_order": 140},
    {"code": "AVAX", "name": "Avalanche", "binance_symbol": "AVAXUSDT", "fallback_market_rate": "60000", "sort_order": 150},
    {"code": "UNI", "name": "Uniswap", "binance_symbol": "UNIUSDT", "fallback_market_rate": "12000", "sort_order": 160},
    {"code": "XLM", "name": "Stellar", "binance_symbol": "XLMUSDT", "fallback_market_rate": "700", "sort_order": 170},
    {"code": "ATOM", "name": "Cosmos", "binance_symbol": "ATOMUSDT", "fallback_market_rate": "8000", "sort_order": 180},
    {"code": "ETC", "name": "Ethereum Classic", "binance_symbol": "ETCUSDT", "fallback_market_rate": "50000", "sort_order": 190},
    {"code": "TON", "name": "Toncoin", "binance_symbol": "TONUSDT", "fallback_market_rate": "7500", "sort_order": 200},
]


def seed_assets_and_rate_configs(apps, schema_editor):
    Asset = apps.get_model("rates", "Asset")
    RateConfiguration = apps.get_model("rates", "RateConfiguration")

    for asset in ASSET_SEED_DATA:
        Asset.objects.update_or_create(
            code=asset["code"],
            defaults={
                "name": asset["name"],
                "binance_symbol": asset["binance_symbol"],
                "sort_order": asset["sort_order"],
                "is_active": True,
            },
        )
        RateConfiguration.objects.get_or_create(
            asset=asset["code"],
            defaults={
                "buy_markup_percent": "3.00",
                "sell_markup_percent": "2.00",
                "fallback_market_rate": asset["fallback_market_rate"],
                "is_active": True,
            },
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('rates', '0003_alter_rateconfiguration_asset_alter_ratequote_asset'),
    ]

    operations = [
        migrations.CreateModel(
            name='Asset',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=10, unique=True)),
                ('name', models.CharField(max_length=100)),
                ('binance_symbol', models.CharField(blank=True, max_length=30)),
                ('broker_wallet_address', models.CharField(blank=True, max_length=255)),
                ('is_active', models.BooleanField(default=True)),
                ('sort_order', models.PositiveSmallIntegerField(default=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['sort_order', 'code'],
            },
        ),
        migrations.RunPython(seed_assets_and_rate_configs, noop_reverse),
        migrations.AlterModelOptions(
            name='rateconfiguration',
            options={'ordering': ['asset__sort_order', 'asset__code']},
        ),
        migrations.RemoveField(
            model_name='rateconfiguration',
            name='is_active',
        ),
        migrations.AlterField(
            model_name='rateconfiguration',
            name='asset',
            field=models.OneToOneField(db_column='asset', on_delete=django.db.models.deletion.CASCADE, related_name='rate_configuration', to='rates.asset', to_field='code'),
        ),
        migrations.AlterField(
            model_name='ratequote',
            name='asset',
            field=models.ForeignKey(db_column='asset', on_delete=django.db.models.deletion.PROTECT, related_name='rate_quotes', to='rates.asset', to_field='code'),
        ),
    ]
