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
