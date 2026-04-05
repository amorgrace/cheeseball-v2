from ninja import Router

from .schemas import AssetSchema, BuyQuoteInputSchema, RateQuoteSchema, SellQuoteInputSchema
from .views import create_buy_quote, create_sell_quote, list_assets

router = Router(tags=["Rates"])


@router.get("/assets", response=list[AssetSchema])
def assets(request):
    return list_assets()


@router.post("/buy-quote", response=RateQuoteSchema)
def buy_quote(request, payload: BuyQuoteInputSchema):
    return create_buy_quote(payload)


@router.post("/sell-quote", response=RateQuoteSchema)
def sell_quote(request, payload: SellQuoteInputSchema):
    return create_sell_quote(payload)
