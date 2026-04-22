from ninja import NinjaAPI

from authenticator.router import router as auth_router
from broker.router import router as broker_router
from payments.router import router as payments_router
from payouts.router import router as payouts_router
from rates.router import router as rates_router
from wallets.router import router as wallets_router

api = NinjaAPI(title="CheeseBall Crypto API", version="1.0.0")

api.add_router("/auth", auth_router)
api.add_router("/rates", rates_router)
api.add_router("/broker", broker_router)
api.add_router("/payouts", payouts_router)
api.add_router("/wallets", wallets_router)
api.add_router("/payments", payments_router)
