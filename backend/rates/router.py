from ninja import Router

from .schemas import AssetSchema, BuyQuoteInputSchema, RateQuoteSchema, SellQuoteInputSchema, UsdNgnRateSchema
from .views import create_buy_quote, create_sell_quote, list_assets
from .services import get_live_usd_ngn_rate

router = Router(tags=["Rates"])


@router.get("/assets", response=list[AssetSchema])
def assets(request):
    return list_assets()


@router.get("/usd-ngn", response=UsdNgnRateSchema)
def usd_ngn(request):
    rate, source = get_live_usd_ngn_rate()
    return {"rate": rate, "source": source}


@router.post("/buy-quote", response=RateQuoteSchema)
def buy_quote(request, payload: BuyQuoteInputSchema):
    return create_buy_quote(payload)


@router.post("/sell-quote", response=RateQuoteSchema)
def sell_quote(request, payload: SellQuoteInputSchema):
    return create_sell_quote(payload)
