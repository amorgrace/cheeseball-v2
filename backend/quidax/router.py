from ninja import Header, Router, Body

from authenticator.auth import JWTAuth

from .schemas import (
    QuidaxDiagnosticSchema,
    QuidaxSubAccountSchema,
    QuidaxWalletAddressCreateSchema,
    QuidaxWalletAddressSchema,
    QuidaxWalletBalanceSchema,
    QuidaxWebhookResponseSchema,
)
from .views import diagnostics, sub_account, webhook, webhook_test, wallet_address, wallet_balance

router = Router(tags=["Quidax"])


@router.post("/webhook", response=QuidaxWebhookResponseSchema)
def quidax_webhook(
    request,
    payload: dict = Body(...),
    quidax_signature: str | None = Header(None, alias="quidax-signature"),
    quidax_timestamp: str | None = Header(None, alias="quidax-timestamp"),
):
    return webhook(request, payload, quidax_signature, quidax_timestamp)


@router.post("/admin/webhook-test", response=QuidaxWebhookResponseSchema, auth=JWTAuth())
def admin_webhook_test(request, payload: dict = Body(...)):
    return webhook_test(request, payload)


@router.get("/admin/diagnostics", response=QuidaxDiagnosticSchema, auth=JWTAuth())
def admin_diagnostics(request):
    return diagnostics(request)


@router.post("/account", response=QuidaxSubAccountSchema, auth=JWTAuth())
def create_or_get_sub_account(request):
    return sub_account(request)


@router.get("/account", response=QuidaxSubAccountSchema, auth=JWTAuth())
def get_or_create_sub_account(request):
    return sub_account(request)


@router.post("/wallet-addresses", response=QuidaxWalletAddressSchema, auth=JWTAuth())
def create_or_get_wallet_address(request, payload: QuidaxWalletAddressCreateSchema):
    return wallet_address(request, payload)


@router.get("/wallet-balance/{currency}", response=QuidaxWalletBalanceSchema, auth=JWTAuth())
def fetch_wallet_balance(request, currency: str):
    return wallet_balance(request, currency)
