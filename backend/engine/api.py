import logging
from ninja import NinjaAPI

from authenticator.router import router as auth_router
from broker.router import router as broker_router
from engine.admin_router import router as admin_router
from kyc.router import router as kyc_router
from payments.router import router as payments_router
from payouts.router import router as payouts_router
from quidax.router import router as quidax_router
from rates.router import router as rates_router
from notifications.router import router as notifications_router
from wallets.router import router as wallets_router
from transfers.router import router as transfers_router
from tatum.router import router as tatum_router

logger = logging.getLogger(__name__)

api = NinjaAPI(title="CheeseBall Crypto API", version="1.0.0")

# --- Exception Handlers ---
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.exceptions import ObjectDoesNotExist
from ninja_jwt.exceptions import TokenError, InvalidToken, AuthenticationFailed
from django_ratelimit.exceptions import Ratelimited

@api.exception_handler(DjangoValidationError)
def django_validation_error_handler(request, exc):
    logger.warning(f"Validation Error: {exc}")
    if hasattr(exc, "message_dict"):
        return api.create_response(request, {"detail": exc.message_dict}, status=400)
    elif hasattr(exc, "messages"):
        return api.create_response(request, {"detail": exc.messages[0]}, status=400)
    else:
        return api.create_response(request, {"detail": str(exc)}, status=400)

@api.exception_handler(ObjectDoesNotExist)
def object_does_not_exist_handler(request, exc):
    logger.warning(f"Object not found: {exc}")
    return api.create_response(request, {"detail": "Not found"}, status=404)

@api.exception_handler(TokenError)
def token_error_handler(request, exc):
    logger.warning(f"Token Error: {exc}")
    return api.create_response(request, {"detail": "Token is invalid or expired"}, status=401)

@api.exception_handler(InvalidToken)
def invalid_token_handler(request, exc):
    logger.warning(f"Invalid Token: {exc}")
    return api.create_response(request, {"detail": "Token is invalid or expired"}, status=401)

@api.exception_handler(AuthenticationFailed)
def authentication_failed_handler(request, exc):
    logger.warning(f"Authentication Failed: {exc}")
    return api.create_response(request, {"detail": str(exc)}, status=401)

@api.exception_handler(ValueError)
def value_error_handler(request, exc):
    logger.warning(f"Value Error: {exc}")
    return api.create_response(request, {"detail": str(exc)}, status=400)

@api.exception_handler(PermissionError)
def permission_error_handler(request, exc):
    logger.warning(f"Permission Error: {exc}")
    return api.create_response(request, {"detail": str(exc)}, status=403)

@api.exception_handler(Ratelimited)
def ratelimited_handler(request, exc):
    logger.warning(f"Rate limited: {request.path}")
    return api.create_response(request, {"detail": "Too many requests. Please try again later."}, status=429)

@api.exception_handler(Exception)
def unhandled_exception_handler(request, exc):
    logger.exception("Unhandled server error")
    return api.create_response(request, {"detail": "An internal server error occurred."}, status=500)
# --------------------------

from giftcards.router import router as giftcards_router

api.add_router("/auth", auth_router)
api.add_router("/rates", rates_router)
api.add_router("/broker", broker_router)
api.add_router("/payouts", payouts_router)
api.add_router("/wallets", wallets_router)
api.add_router("/payments", payments_router)
api.add_router("/kyc", kyc_router)
api.add_router("/quidax", quidax_router)
api.add_router("/notifications", notifications_router)
api.add_router("/transfers", transfers_router)
api.add_router("/giftcards", giftcards_router)
api.add_router("/admin", admin_router)
api.add_router("/tatum", tatum_router)  # HD wallet + Tatum monitoring (dual-run alongside quidax)
