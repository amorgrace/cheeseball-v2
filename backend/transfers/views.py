from uuid import UUID

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from ninja.responses import Response

from rates.models import Asset
from .models import CryptoTransfer
from .schemas import TransferCreateSchema, AdminTransferActionSchema
from .services import initiate_internal_transfer, initiate_external_transfer, admin_approve_transfer, admin_reject_transfer

User = get_user_model()


def serialize_transfer(transfer: CryptoTransfer) -> dict:
    return {
        "id": transfer.id,
        "transfer_type": transfer.transfer_type,
        "asset": transfer.asset_id,
        "amount": transfer.amount,
        "status": transfer.status,
        "recipient_email": transfer.recipient.email if transfer.recipient else None,
        "recipient_address": transfer.recipient_address,
        "recipient_network": transfer.recipient_network,
        "failure_reason": transfer.failure_reason,
        "admin_notes": transfer.admin_notes,
        "created_at": transfer.created_at.isoformat(),
        "reviewed_at": transfer.reviewed_at.isoformat() if transfer.reviewed_at else None,
        "completed_at": transfer.completed_at.isoformat() if transfer.completed_at else None,
    }


def create_transfer(request, payload: TransferCreateSchema):
    asset = get_object_or_404(Asset, code=payload.asset)
    
    try:
        if payload.transfer_type == "internal":
            if payload.recipient_id:
                recipient = get_object_or_404(User, id=payload.recipient_id)
            else:
                recipient = get_object_or_404(User, email__iexact=payload.recipient_email)
                
            transfer = initiate_internal_transfer(
                sender=request.auth,
                recipient=recipient,
                asset=asset,
                amount=payload.amount,
            )
        else:
            transfer = initiate_external_transfer(
                sender=request.auth,
                asset=asset,
                amount=payload.amount,
                recipient_address=payload.recipient_address,
                recipient_network=payload.recipient_network,
            )
        return serialize_transfer(transfer)
    except ValidationError as e:
        return Response({"detail": str(e)}, status=400)


def list_user_transfers(request):
    transfers = CryptoTransfer.objects.filter(sender=request.auth)
    return [serialize_transfer(t) for t in transfers]


def get_transfer_detail(request, transfer_id: UUID):
    transfer = get_object_or_404(CryptoTransfer, id=transfer_id)
    if not request.auth.is_staff and transfer.sender_id != request.auth.id:
        return Response({"detail": "Not found."}, status=404)
    return serialize_transfer(transfer)


# --- Admin ---

def admin_list_pending_transfers(request):
    from broker.services import ensure_admin
    ensure_admin(request.auth)
    transfers = CryptoTransfer.objects.filter(status=CryptoTransfer.PENDING_REVIEW)
    return [serialize_transfer(t) for t in transfers]


def admin_approve(request, transfer_id: UUID):
    from broker.services import ensure_admin
    ensure_admin(request.auth)
    transfer = get_object_or_404(CryptoTransfer, id=transfer_id)
    try:
        transfer = admin_approve_transfer(transfer, request.auth)
        return serialize_transfer(transfer)
    except ValidationError as e:
        return Response({"detail": str(e)}, status=400)


def admin_reject(request, transfer_id: UUID, payload: AdminTransferActionSchema):
    from broker.services import ensure_admin
    ensure_admin(request.auth)
    transfer = get_object_or_404(CryptoTransfer, id=transfer_id)
    try:
        transfer = admin_reject_transfer(transfer, request.auth, reason=payload.reason)
        return serialize_transfer(transfer)
    except ValidationError as e:
        return Response({"detail": str(e)}, status=400)
