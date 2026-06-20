from uuid import UUID

from ninja import Router

from authenticator.auth import JWTAuth
from .schemas import TransferCreateSchema, TransferResponseSchema, AdminTransferActionSchema
from .views import (
    create_transfer,
    list_user_transfers,
    get_transfer_detail,
    admin_list_pending_transfers,
    admin_approve,
    admin_reject,
)

router = Router(tags=["Transfers"])


@router.post("/send", response=TransferResponseSchema, auth=JWTAuth())
def initiate_transfer_endpoint(request, payload: TransferCreateSchema):
    return create_transfer(request, payload)


@router.get("/", response=list[TransferResponseSchema], auth=JWTAuth())
def list_transfers_endpoint(request):
    return list_user_transfers(request)


@router.get("/{transfer_id}", response=TransferResponseSchema, auth=JWTAuth())
def get_transfer_endpoint(request, transfer_id: UUID):
    return get_transfer_detail(request, transfer_id)


# --- Admin ---

@router.get("/admin/pending-review", response=list[TransferResponseSchema], auth=JWTAuth())
def admin_pending_transfers_endpoint(request):
    return admin_list_pending_transfers(request)


@router.post("/admin/{transfer_id}/approve", response=TransferResponseSchema, auth=JWTAuth())
def admin_approve_transfer_endpoint(request, transfer_id: UUID):
    return admin_approve(request, transfer_id)


@router.post("/admin/{transfer_id}/reject", response=TransferResponseSchema, auth=JWTAuth())
def admin_reject_transfer_endpoint(request, transfer_id: UUID, payload: AdminTransferActionSchema):
    return admin_reject(request, transfer_id, payload)
