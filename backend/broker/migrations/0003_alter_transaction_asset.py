

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('broker', '0002_alter_transaction_asset'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transaction',
            name='asset',
            field=models.CharField(choices=[('BTC', 'Bitcoin'), ('ETH', 'Ethereum'), ('USDT', 'Tether'), ('BNB', 'BNB'), ('SOL', 'Solana'), ('XRP', 'XRP'), ('TRX', 'TRON'), ('LTC', 'Litecoin'), ('DOGE', 'Dogecoin'), ('BCH', 'Bitcoin Cash'), ('ADA', 'Cardano'), ('MATIC', 'Polygon'), ('DOT', 'Polkadot'), ('LINK', 'Chainlink'), ('AVAX', 'Avalanche'), ('UNI', 'Uniswap'), ('XLM', 'Stellar'), ('ATOM', 'Cosmos'), ('ETC', 'Ethereum Classic'), ('TON', 'Toncoin')], default='BTC', max_length=10),
        ),
    ]
