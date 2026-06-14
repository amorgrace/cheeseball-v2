from uuid import UUID

from ninja import Router

from authenticator.auth import JWTAuth
from broker.schemas import RejectTransactionSchema

from .schemas import (
    BalanceSummarySchema,
    ConversionCreateSchema,
    ConversionExecuteSchema,
    ConversionPreviewSchema,
    ConversionSchema,
    UserWalletSchema,
    WalletBalanceSchema,
    WithdrawalActionSchema,
    WithdrawalCreateSchema,
    WithdrawalSchema,
    DepositCreateSchema,
    DepositResponseSchema,
    DepositDetailSchema,
    AdminDepositCompleteSchema,
)
from .views import (
    approve_withdrawal,
    execute_conversion,
    get_balance_summary,
    get_user_wallets,
    get_wallet_balance,
    get_withdrawal,
    initiate_withdrawal,
    list_withdrawals,
    preview_conversion,
    reject_withdrawal,
    create_deposit,
    get_deposit,
    admin_list_deposits,
    admin_complete_deposit,
)

router = Router(tags=["Wallets"])


@router.post("/convert/preview", response=ConversionPreviewSchema, auth=JWTAuth())
def preview_convert(request, payload: ConversionCreateSchema):
    return preview_conversion(request, payload)


@router.post("/convert", response=ConversionSchema, auth=JWTAuth())
def execute_convert(request, payload: ConversionExecuteSchema):
    return execute_conversion(request, payload)


@router.post("/withdrawals", response=WithdrawalSchema, auth=JWTAuth())
def create_withdrawal_endpoint(request, payload: WithdrawalCreateSchema):
    return initiate_withdrawal(request, payload)


@router.get("/withdrawals", response=list[WithdrawalSchema], auth=JWTAuth())
def list_user_withdrawals(request):
    return list_withdrawals(request)


@router.get("/withdrawals/{withdrawal_id}", response=WithdrawalSchema, auth=JWTAuth())
def withdrawal_detail(request, withdrawal_id: UUID):
    return get_withdrawal(request, withdrawal_id)


@router.post("/admin/withdrawals/{withdrawal_id}/approve", response=WithdrawalSchema, auth=JWTAuth())
def admin_approve_withdrawal(request, withdrawal_id: UUID, payload: WithdrawalActionSchema):
    return approve_withdrawal(request, withdrawal_id, payload)


@router.post("/admin/withdrawals/{withdrawal_id}/reject", response=WithdrawalSchema, auth=JWTAuth())
def admin_reject_withdrawal(request, withdrawal_id: UUID, payload: RejectTransactionSchema):
    return reject_withdrawal(request, withdrawal_id, payload)


@router.get("/wallets", response=UserWalletSchema, auth=JWTAuth())
def get_wallets(request):
    return get_user_wallets(request)


@router.get("/wallets/{asset_code}", response=WalletBalanceSchema, auth=JWTAuth())
def get_wallet(request, asset_code: str):
    return get_wallet_balance(request, asset_code)


@router.get("/balances/summary", response=BalanceSummarySchema, auth=JWTAuth())
def balance_summary(request):
    return get_balance_summary(request)



@router.post("/deposits/create", response=DepositResponseSchema, auth=JWTAuth())
def deposit_create(request, payload: DepositCreateSchema):
    return create_deposit(request, payload)


@router.get("/deposits/{deposit_id}", response=DepositDetailSchema, auth=JWTAuth())
def deposit_detail(request, deposit_id: str):
    return get_deposit(request, deposit_id)


@router.get("/admin/deposits", response=list[DepositDetailSchema], auth=JWTAuth())
def admin_deposits_list(request, status: str | None = None):
    return admin_list_deposits(request, status)


@router.post("/admin/deposits/{deposit_id}/complete", response=DepositDetailSchema, auth=JWTAuth())
def admin_deposit_complete(request, deposit_id: str, payload: AdminDepositCompleteSchema):
    return admin_complete_deposit(request, deposit_id, payload)


from .schemas import WalletFundingCreateSchema, WalletFundingResponseSchema
from .views import fund_ngn_wallet

@router.post("/fund/ngn", response=WalletFundingResponseSchema, auth=JWTAuth())
def fund_ngn(request, payload: WalletFundingCreateSchema):
    return fund_ngn_wallet(request, payload)


# --- Treasury (admin + cron) ---
from ninja.security import HttpBearer
from .views import sync_treasury, get_reconciliation


class CronOrJWTAuth(HttpBearer):
    """Allows either a valid JWT (staff) or the X-Cron-Secret header."""
    def authenticate(self, request, token):
        # HttpBearer extracts Bearer token; we also check the cron header
        from .views import _is_cron_authenticated
        if _is_cron_authenticated(request):
            return "cron"
        # Fall back to JWT
        from authenticator.auth import JWTAuth as _JWTAuth
        import asyncio
        loop = asyncio.new_event_loop()
        user = loop.run_until_complete(_JWTAuth()(request))
        loop.close()
        return user


@router.post("/admin/treasury/sync", auth=None)
def treasury_sync(request):
    return sync_treasury(request)


@router.get("/admin/treasury/reconciliation", auth=JWTAuth())
def treasury_reconciliation(request):
    return get_reconciliation(request)

