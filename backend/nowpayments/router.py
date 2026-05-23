from ninja import Header, Router

from authenticator.auth import JWTAuth

from .schemas import (
    CustodyAccountSchema,
    CustodyBalanceSchema,
    CustodyDepositCreateSchema,
    CustodyDepositSchema,
    NowPaymentsDiagnosticSchema,
    NowPaymentsIPNSchema,
)
from .views import custody_account, custody_balance, custody_deposit, diagnostics, nowpayments_ipn

router = Router(tags=["NOWPayments"])


@router.post("/ipn/")
def ipn(
    request,
    payload: NowPaymentsIPNSchema,
    x_nowpayments_sig: str | None = Header(None, alias="x-nowpayments-sig"),
):
    return nowpayments_ipn(request, payload, x_nowpayments_sig)


@router.get("/admin/diagnostics", response=NowPaymentsDiagnosticSchema, auth=JWTAuth())
def admin_diagnostics(request):
    return diagnostics(request)


@router.post("/custody/account", response=CustodyAccountSchema, auth=JWTAuth())
def create_or_get_custody_account(request):
    return custody_account(request)


@router.get("/custody/balance", response=CustodyBalanceSchema, auth=JWTAuth())
def get_user_custody_balance(request):
    return custody_balance(request)


@router.post("/custody/deposits", response=CustodyDepositSchema, auth=JWTAuth())
def create_user_custody_deposit(request, payload: CustodyDepositCreateSchema):
    return custody_deposit(request, payload)
