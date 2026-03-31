from ninja import NinjaAPI

from authenticator.router import router as auth_router

api = NinjaAPI(title="CheeseBall Crypto API", version="1.0.0")

api.add_router("/auth", auth_router)
