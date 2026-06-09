import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'engine.settings')
django.setup()

from django.test import Client, RequestFactory
from authenticator.models import CustomUser
from rates.models import RateQuote, Asset
import decimal

asset = Asset.objects.filter(code="BTC").first()
import datetime
from django.utils import timezone
from authenticator.models import CustomUser

user = CustomUser.objects.first()
quote = RateQuote.objects.create(
    asset=asset,
    quote_type=RateQuote.SELL,
    crypto_amount=decimal.Decimal("0.01"),
    naira_amount=decimal.Decimal("1000000"),
    market_rate=decimal.Decimal("100000000"),
    markup_percent=decimal.Decimal("2"),
    final_rate=decimal.Decimal("98000000"),
    crypto_usd_price=decimal.Decimal("60000"),
    expires_at=timezone.now() + datetime.timedelta(minutes=5)
)

factory = RequestFactory()
payload = {
    "quote_id": quote.id if quote else 1,
    "crypto_source": "external_wallet",
    "payout_method": "ngn_wallet",
    "beneficiary_id": None,
    "promo_code": None,
    "promo_benefit": 0,
}

request = factory.post("/api/broker/sell", data=json.dumps(payload), content_type="application/json")
request.auth = user

from broker.schemas import SellTransactionCreateSchema

payload_schema = SellTransactionCreateSchema(**payload)

response = create_sell_transaction(request, payload_schema)

import json
if hasattr(response, 'content'):
    print(f"Content: {response.content.decode()}")

