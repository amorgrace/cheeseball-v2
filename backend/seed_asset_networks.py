"""
Seed correct default networks for each asset in the DB.
Only updates assets that currently have no network set.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'engine.settings')
django.setup()

from rates.models import Asset

NETWORK_MAP = {
    "BTC":  "Bitcoin",
    "ETH":  "ERC20",
    "USDT": "TRC20",
    "USDC": "ERC20",
    "BNB":  "BEP20",
    "SOL":  "Solana",
    "XRP":  "XRP",
    "TRX":  "TRC20",
    "LTC":  "Litecoin",
    "DOGE": "Dogecoin",
    "BCH":  "Bitcoin Cash",
    "ADA":  "Cardano",
    "LINK": "ERC20",
    "XLM":  "Stellar",
    "TON":  "TON",
    # These are not supported by Quidax deposits, but set a default anyway
    "MATIC": "Polygon",
    "DOT":   "Polkadot",
    "AVAX":  "Avalanche",
    "UNI":   "ERC20",
    "ATOM":  "Cosmos",
    "ETC":   "ETC",
}

updated = 0
for asset in Asset.objects.exclude(code="NGN"):
    if not asset.network and asset.code in NETWORK_MAP:
        asset.network = NETWORK_MAP[asset.code]
        asset.save(update_fields=["network"])
        print(f"Updated {asset.code} -> network={asset.network}")
        updated += 1
    else:
        print(f"Skipped {asset.code}: already has network={repr(asset.network)}")

print(f"\nDone. Updated {updated} assets.")
