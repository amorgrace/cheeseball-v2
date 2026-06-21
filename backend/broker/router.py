
from ninja import Router
from ninja.pagination import paginate, PageNumberPagination

from authenticator.auth import JWTAuth

from .schemas import BuyTransactionCreateSchema, RejectTransactionSchema, SellTransactionCreateSchema, TransactionActionSchema, TransactionSchema
from .views import (
    approve_transaction,
    complete_transaction,
    confirm_sell_crypto_sent,
    create_buy_transaction,
    create_sell_transaction,
    fail_transaction,
    get_transaction,
    list_transactions,
    reject_transaction,
    expire_stale_transactions_view,
)

router = Router(tags=["Broker"])


@router.post("/buy", response=TransactionSchema, auth=JWTAuth())
def create_buy(request, payload: BuyTransactionCreateSchema):
    return create_buy_transaction(request, payload)


@router.post("/sell", response=TransactionSchema, auth=JWTAuth())
def create_sell(request, payload: SellTransactionCreateSchema):
    return create_sell_transaction(request, payload)


@router.get("/transactions", response=list[TransactionSchema], auth=JWTAuth())
@paginate(PageNumberPagination, page_size=10)
def transactions(request):
    return list_transactions(request)


@router.get("/transactions/{transaction_id}", response=TransactionSchema, auth=JWTAuth())
def transaction_detail(request, transaction_id: str):
    return get_transaction(request, transaction_id)


@router.post("/transactions/{transaction_id}/confirm-crypto-sent", response=TransactionSchema, auth=JWTAuth())
def confirm_crypto_sent(request, transaction_id: str):
    return confirm_sell_crypto_sent(request, transaction_id)


@router.post("/admin/transactions/{transaction_id}/approve", response=TransactionSchema, auth=JWTAuth())
def admin_approve(request, transaction_id: str, payload: TransactionActionSchema):
    return approve_transaction(request, transaction_id, payload)


@router.post("/admin/transactions/{transaction_id}/reject", response=TransactionSchema, auth=JWTAuth())
def admin_reject(request, transaction_id: str, payload: RejectTransactionSchema):
    return reject_transaction(request, transaction_id, payload)


@router.post("/admin/transactions/{transaction_id}/complete", response=TransactionSchema, auth=JWTAuth())
def admin_complete(request, transaction_id: str, payload: TransactionActionSchema):
    return complete_transaction(request, transaction_id, payload)


@router.post("/admin/transactions/{transaction_id}/fail", response=TransactionSchema, auth=JWTAuth())
def admin_fail(request, transaction_id: str, payload: TransactionActionSchema):
    return fail_transaction(request, transaction_id, payload)


@router.get("/cron/expire-transactions")
def expire_transactions_cron(request):
    """Cron endpoint to expire stale pending transactions. No auth required since it only performs a safe automated task."""
    return expire_stale_transactions_view(request)

