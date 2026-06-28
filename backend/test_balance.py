import os
import django
import json

from django.contrib.auth import get_user_model
from wallets.models import WalletBalance

User = get_user_model()
try:
    user = User.objects.get(email='allilrizzy@yahoo.com')
    wb = WalletBalance.objects.get(user=user, asset__code='NGN')
    print(json.dumps({
        "balance": str(wb.balance),
        "locked_balance": str(wb.locked_balance),
        "available_balance": str(wb.available_balance)
    }))
except Exception as e:
    print(str(e))
