import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'engine.settings')
django.setup()

from quidax.services import ensure_sub_account, ensure_wallet_address
from authenticator.models import CustomUser
from rates.models import Asset

user = CustomUser.objects.first()

assets = Asset.objects.all()
for asset in assets:
    if asset.code == "NGN":
        continue
    try:
        wallet = ensure_wallet_address(user, currency=asset.code, network=asset.network)
        print(f"Success for {asset.code} on {asset.network}: {wallet.address}")
    except Exception as e:
        print(f"Failed for {asset.code} on {asset.network}: {e}")
