"""
transfers/services.py

Business logic for crypto transfers:
  - Internal (user-to-user in-app): pure ledger, no Quidax
  - External (on-chain): calls Quidax, or queues for admin review if liquidity insufficient
"""
import logging

from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction as db_transaction
from django.utils import timezone

from .models import CryptoTransfer

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------

def _assert_kyc_verified(user):
    if user.kyc_status != "verified":
        raise ValidationError("KYC verification is required to send crypto.")


def _assert_send_enabled(asset):
    if not asset.send_enabled:
        raise ValidationError(f"{asset.code} is not currently available for sending.")


def _assert_not_self(sender, recipient):
    if sender.id == recipient.id:
        raise ValidationError("You cannot send crypto to yourself.")


# ---------------------------------------------------------------------------
# Internal transfer (free, ledger-only)
# ---------------------------------------------------------------------------

@db_transaction.atomic
def initiate_internal_transfer(*, sender, recipient, asset, amount) -> CryptoTransfer:
    """
    Transfer crypto between two Cheeseball users.
    Completely free — no Quidax involved, no PlatformReserve change.
    """
    from wallets.services import get_user_wallet
    from wallets.models import Ledger

    _assert_kyc_verified(sender)
    _assert_send_enabled(asset)
    _assert_not_self(sender, recipient)

    if amount <= 0:
        raise ValidationError("Transfer amount must be greater than zero.")

    sender_wallet = get_user_wallet(sender, asset)
    if sender_wallet.available_balance < amount:
        raise ValidationError(f"Insufficient {asset.code} balance.")

    recipient_wallet = get_user_wallet(recipient, asset)

    # Debit sender
    sender_wallet.balance -= amount
    sender_wallet.save(update_fields=["balance", "updated_at"])
    Ledger.objects.create(
        user=sender,
        wallet_balance=sender_wallet,
        transaction_type=Ledger.WALLET_WITHDRAWAL,
        amount=amount,
        balance_before=sender_wallet.balance + amount,
        balance_after=sender_wallet.balance,
        locked_before=sender_wallet.locked_balance,
        locked_after=sender_wallet.locked_balance,
        reference_model="CryptoTransfer",
        notes=f"Send to {recipient.email}",
    )

    # Credit recipient
    recipient_wallet.balance += amount
    recipient_wallet.save(update_fields=["balance", "updated_at"])
    Ledger.objects.create(
        user=recipient,
        wallet_balance=recipient_wallet,
        transaction_type=Ledger.WALLET_DEPOSIT,
        amount=amount,
        balance_before=recipient_wallet.balance - amount,
        balance_after=recipient_wallet.balance,
        locked_before=recipient_wallet.locked_balance,
        locked_after=recipient_wallet.locked_balance,
        reference_model="CryptoTransfer",
        notes=f"Received from {sender.email}",
    )

    transfer = CryptoTransfer.objects.create(
        sender=sender,
        recipient=recipient,
        asset=asset,
        amount=amount,
        transfer_type=CryptoTransfer.INTERNAL,
        status=CryptoTransfer.COMPLETED,
        completed_at=timezone.now(),
    )

    _notify_transfer(transfer)
    return transfer


# ---------------------------------------------------------------------------
# External transfer (on-chain)
# ---------------------------------------------------------------------------

@db_transaction.atomic
def initiate_external_transfer(*, sender, asset, amount, recipient_address, recipient_network) -> CryptoTransfer:
    """
    Send crypto to an external wallet address.

    - If asset.withdrawal_mode == 'manual' OR PlatformReserve < amount:
        → lock funds, create transfer in PENDING_REVIEW
    - Otherwise:
        → debit wallet + reserve, call Quidax, mark COMPLETED
    """
    from wallets.services import get_user_wallet
    from wallets.models import Ledger, PlatformReserve

    _assert_kyc_verified(sender)
    _assert_send_enabled(asset)

    if not recipient_address:
        raise ValidationError("Recipient wallet address is required.")
    if amount <= 0:
        raise ValidationError("Transfer amount must be greater than zero.")

    wallet = get_user_wallet(sender, asset)
    if wallet.available_balance < amount:
        raise ValidationError(f"Insufficient {asset.code} balance.")

    # Determine if we can auto-process
    force_manual = asset.withdrawal_mode == asset.WITHDRAWAL_MODE_MANUAL
    try:
        reserve = PlatformReserve.objects.get(asset=asset)
        sufficient_liquidity = reserve.balance >= amount
    except PlatformReserve.DoesNotExist:
        sufficient_liquidity = False

    if force_manual or not sufficient_liquidity:
        return _queue_for_review(
            sender=sender,
            wallet=wallet,
            asset=asset,
            amount=amount,
            recipient_address=recipient_address,
            recipient_network=recipient_network,
            reason="manual" if force_manual else "insufficient_liquidity",
        )

    return _execute_external_transfer(
        sender=sender,
        wallet=wallet,
        asset=asset,
        amount=amount,
        recipient_address=recipient_address,
        recipient_network=recipient_network,
    )


def _queue_for_review(*, sender, wallet, asset, amount, recipient_address, recipient_network, reason) -> CryptoTransfer:
    """Lock user funds and create a PENDING_REVIEW transfer."""
    from wallets.models import Ledger

    # Lock the funds
    wallet.locked_balance += amount
    wallet.save(update_fields=["locked_balance", "updated_at"])
    Ledger.objects.create(
        user=sender,
        wallet_balance=wallet,
        transaction_type=Ledger.WITHDRAWAL_LOCK,
        amount=amount,
        balance_before=wallet.balance,
        balance_after=wallet.balance,
        locked_before=wallet.locked_balance - amount,
        locked_after=wallet.locked_balance,
        reference_model="CryptoTransfer",
        notes=f"Locked for pending review ({reason})",
    )

    transfer = CryptoTransfer.objects.create(
        sender=sender,
        asset=asset,
        amount=amount,
        transfer_type=CryptoTransfer.EXTERNAL,
        recipient_address=recipient_address,
        recipient_network=recipient_network,
        status=CryptoTransfer.PENDING_REVIEW,
        failure_reason=reason,
    )

    _notify_pending_review(transfer)
    return transfer


def _execute_external_transfer(*, sender, wallet, asset, amount, recipient_address, recipient_network) -> CryptoTransfer:
    """Debit wallet + reserve, call Quidax, mark completed."""
    from wallets.models import Ledger, PlatformReserve, ReserveMovement

    # Create the transfer record first (we'll update status after Quidax)
    transfer = CryptoTransfer.objects.create(
        sender=sender,
        asset=asset,
        amount=amount,
        transfer_type=CryptoTransfer.EXTERNAL,
        recipient_address=recipient_address,
        recipient_network=recipient_network,
        status=CryptoTransfer.PENDING,
    )

    try:
        from django.conf import settings
        crypto_provider = getattr(settings, "CRYPTO_PROVIDER", "quidax")

        if crypto_provider == "hd_tatum":
            from hd_wallets.services import broadcast_on_chain_withdrawal
            on_chain_withdrawal = broadcast_on_chain_withdrawal(
                sender,
                currency=asset.code,
                amount=amount,
                to_address=recipient_address,
                network=recipient_network,
            )
            transfer.admin_notes = f"OnChain Tx: {on_chain_withdrawal.txid or on_chain_withdrawal.id}"
        else:
            from quidax.services import initiate_crypto_withdrawal
            quidax_response = initiate_crypto_withdrawal(
                sender,
                currency=asset.code,
                amount=amount,
                fund_uid=recipient_address,
                network=recipient_network,
            )
            transfer.admin_notes = f"Quidax Tx: {quidax_response.get('id') or quidax_response}"
    except Exception as exc:
        logger.exception("Quidax withdrawal failed for transfer %s", transfer.id)
        transfer.status = CryptoTransfer.FAILED
        transfer.failure_reason = str(exc)
        transfer.save(update_fields=["status", "failure_reason", "admin_notes", "updated_at"])
        raise ValidationError(f"On-chain send failed: {exc}")

    # Debit wallet
    wallet.balance -= amount
    wallet.save(update_fields=["balance", "updated_at"])
    Ledger.objects.create(
        user=sender,
        wallet_balance=wallet,
        transaction_type=Ledger.WALLET_WITHDRAWAL,
        amount=amount,
        balance_before=wallet.balance + amount,
        balance_after=wallet.balance,
        locked_before=wallet.locked_balance,
        locked_after=wallet.locked_balance,
        reference_model="CryptoTransfer",
        notes=f"External send to {recipient_address}",
    )

    # Debit reserve
    reserve, _ = PlatformReserve.objects.get_or_create(asset=asset)
    reserve.balance -= amount
    reserve.save(update_fields=["balance"])
    ReserveMovement.objects.create(
        asset=asset,
        movement_type=ReserveMovement.OUT,
        amount=amount,
        notes=f"External send CryptoTransfer {transfer.id}",
    )

    transfer.status = CryptoTransfer.COMPLETED
    transfer.completed_at = timezone.now()
    transfer.save(update_fields=["status", "completed_at", "admin_notes", "updated_at"])

    _notify_transfer(transfer)
    return transfer


# ---------------------------------------------------------------------------
# Admin actions
# ---------------------------------------------------------------------------

def admin_approve_transfer(transfer: CryptoTransfer, admin_user) -> CryptoTransfer:
    """
    Admin approves a PENDING_REVIEW external transfer.
    Calls Quidax, unlocks funds, debits wallet + reserve.
    """
    if transfer.status != CryptoTransfer.PENDING_REVIEW:
        raise ValidationError(f"Cannot approve a transfer with status '{transfer.status}'.")
    if transfer.transfer_type != CryptoTransfer.EXTERNAL:
        raise ValidationError("Only external transfers require admin approval.")

    from wallets.services import get_user_wallet
    from wallets.models import Ledger, PlatformReserve, ReserveMovement

    with db_transaction.atomic():
        wallet = get_user_wallet(transfer.sender, transfer.asset)

        # Call on-chain send
        try:
            from django.conf import settings
            crypto_provider = getattr(settings, "CRYPTO_PROVIDER", "quidax")

            if crypto_provider == "hd_tatum":
                from hd_wallets.services import broadcast_on_chain_withdrawal
                on_chain_withdrawal = broadcast_on_chain_withdrawal(
                    transfer.sender,
                    currency=transfer.asset.code,
                    amount=transfer.amount,
                    to_address=transfer.recipient_address,
                    network=transfer.recipient_network,
                )
                notes = f"OnChain Tx: {on_chain_withdrawal.txid or on_chain_withdrawal.id}"
            else:
                from quidax.services import initiate_crypto_withdrawal
                quidax_response = initiate_crypto_withdrawal(
                    transfer.sender,
                    currency=transfer.asset.code,
                    amount=transfer.amount,
                    fund_uid=transfer.recipient_address,
                    network=transfer.recipient_network,
                )
                notes = f"Quidax Tx: {quidax_response.get('id') or quidax_response}"
        except Exception as exc:
            logger.exception("Admin-approved Quidax withdrawal failed for transfer %s", transfer.id)
            raise ValidationError(f"On-chain send failed: {exc}")

        # Unlock then debit (net: subtract from balance, clear lock)
        wallet.locked_balance -= transfer.amount
        wallet.balance -= transfer.amount
        wallet.save(update_fields=["balance", "locked_balance", "updated_at"])

        Ledger.objects.create(
            user=transfer.sender,
            wallet_balance=wallet,
            transaction_type=Ledger.WITHDRAWAL_DEBIT,
            amount=transfer.amount,
            balance_before=wallet.balance + transfer.amount,
            balance_after=wallet.balance,
            locked_before=wallet.locked_balance + transfer.amount,
            locked_after=wallet.locked_balance,
            reference_model="CryptoTransfer",
            notes=f"Admin-approved external send {transfer.id}",
        )

        # Debit reserve
        reserve, _ = PlatformReserve.objects.get_or_create(asset=transfer.asset)
        reserve.balance -= transfer.amount
        reserve.save(update_fields=["balance"])
        ReserveMovement.objects.create(
            asset=transfer.asset,
            movement_type=ReserveMovement.OUT,
            amount=transfer.amount,
            notes=f"Admin-approved send CryptoTransfer {transfer.id}",
        )

        transfer.status = CryptoTransfer.COMPLETED
        transfer.completed_at = timezone.now()
        transfer.reviewed_by = admin_user
        transfer.reviewed_at = timezone.now()
        transfer.admin_notes = notes
        transfer.save(update_fields=["status", "completed_at", "reviewed_by", "reviewed_at", "admin_notes", "updated_at"])

    _notify_transfer(transfer)
    return transfer


def admin_reject_transfer(transfer: CryptoTransfer, admin_user, reason: str = "") -> CryptoTransfer:
    """
    Admin rejects a PENDING_REVIEW transfer — unlocks and returns funds to sender.
    """
    if transfer.status != CryptoTransfer.PENDING_REVIEW:
        raise ValidationError(f"Cannot reject a transfer with status '{transfer.status}'.")

    from wallets.services import get_user_wallet
    from wallets.models import Ledger

    with db_transaction.atomic():
        wallet = get_user_wallet(transfer.sender, transfer.asset)

        # Unlock funds
        wallet.locked_balance -= transfer.amount
        wallet.save(update_fields=["locked_balance", "updated_at"])

        Ledger.objects.create(
            user=transfer.sender,
            wallet_balance=wallet,
            transaction_type=Ledger.WITHDRAWAL_RELEASE,
            amount=transfer.amount,
            balance_before=wallet.balance,
            balance_after=wallet.balance,
            locked_before=wallet.locked_balance + transfer.amount,
            locked_after=wallet.locked_balance,
            reference_model="CryptoTransfer",
            notes=f"Admin-rejected, funds unlocked: {transfer.id}",
        )

        transfer.status = CryptoTransfer.CANCELLED
        transfer.failure_reason = reason or "Rejected by admin"
        transfer.reviewed_by = admin_user
        transfer.reviewed_at = timezone.now()
        transfer.save(update_fields=["status", "failure_reason", "reviewed_by", "reviewed_at", "updated_at"])

    _notify_rejected(transfer)
    return transfer


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

def _notify_transfer(transfer: CryptoTransfer):
    from notifications.services import notify
    from notifications.models import Notification
    from django.utils import timezone as _tz

    amount = transfer.amount
    code = transfer.asset_id
    _local_dt = _tz.localtime(transfer.completed_at or _tz.now())
    _fdate = _local_dt.strftime("%m/%d/%Y, %I:%M %p")

    if transfer.transfer_type == CryptoTransfer.INTERNAL:
        _type_label = "Internal transfer"
        # Notify sender
        notify(
            transfer.sender,
            title="Crypto Sent",
            message=f"You successfully sent {amount} {code} to {transfer.recipient.email}.",
            notification_type=Notification.CRYPTO_SENT,
            reference_id=transfer.id,
            reference_type="CryptoTransfer",
            extra_context={
                "template_name": "emails/crypto_sent.html",
                "text_template_name": "emails/crypto_sent.txt",
                "amount": str(amount),
                "asset_code": code,
                "recipient": transfer.recipient.email,
                "transfer_type": _type_label,
                "formatted_date": _fdate,
                "cta_url": "https://cheeseballapp.com/dashboard/transfers",
            },
        )
        # Notify recipient
        if transfer.recipient:
            notify(
                transfer.recipient,
                title="Crypto Received",
                message=f"You received {amount} {code} from {transfer.sender.email}.",
                notification_type=Notification.CRYPTO_RECEIVED,
                reference_id=transfer.id,
                reference_type="CryptoTransfer",
                extra_context={
                    "template_name": "emails/crypto_received.html",
                    "text_template_name": "emails/crypto_received.txt",
                    "amount": str(amount),
                    "asset_code": code,
                    "sender": transfer.sender.email,
                    "formatted_date": _fdate,
                    "cta_url": "https://cheeseballapp.com/dashboard/wallets",
                },
            )
    else:
        notify(
            transfer.sender,
            title="Crypto Sent",
            message=f"Your transfer of {amount} {code} to {transfer.recipient_address} was completed.",
            notification_type=Notification.CRYPTO_SENT,
            reference_id=transfer.id,
            reference_type="CryptoTransfer",
            extra_context={
                "template_name": "emails/crypto_sent.html",
                "text_template_name": "emails/crypto_sent.txt",
                "amount": str(amount),
                "asset_code": code,
                "recipient": transfer.recipient_address,
                "transfer_type": "External transfer",
                "formatted_date": _fdate,
                "cta_url": "https://cheeseballapp.com/dashboard/transfers",
            },
        )


def _notify_pending_review(transfer: CryptoTransfer):
    from notifications.services import notify
    from notifications.models import Notification

    notify(
        transfer.sender,
        title="Transfer Pending Review",
        message=(
            f"Your transfer of {transfer.amount} {transfer.asset_id} is pending admin review "
            f"due to liquidity constraints. Your funds have been locked and are safe."
        ),
        notification_type=Notification.GENERAL,
        reference_id=transfer.id,
        reference_type="CryptoTransfer",
    )

    # Send Admin Telegram Notification
    try:
        import html
        from django.utils import timezone as _tz
        from notifications.telegram import send_telegram_alert
        _ts = _tz.now().strftime("%Y-%m-%d %H:%M UTC")
        telegram_msg = (
            f"⚠️ <b>TRANSFER FLAGGED FOR REVIEW</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 Sender: {html.escape(transfer.sender.email)}\n"
            f"💰 Amount: {transfer.amount} {html.escape(transfer.asset_id or '')}\n"
            f"📬 Recipient: {html.escape(transfer.recipient_address)}\n"
            f"🌐 Network: {html.escape(transfer.recipient_network)}\n"
            f"📌 Reason: Liquidity Constraint\n"
            f"⏰ {_ts}"
        )
        send_telegram_alert(telegram_msg)
    except Exception:
        pass


def _notify_rejected(transfer: CryptoTransfer):
    from notifications.services import notify
    from notifications.models import Notification

    notify(
        transfer.sender,
        title="Transfer Cancelled",
        message=(
            f"Your transfer of {transfer.amount} {transfer.asset_id} was cancelled. "
            f"Your funds have been returned to your wallet. "
            f"Reason: {transfer.failure_reason or 'No reason provided.'}"
        ),
        notification_type=Notification.GENERAL,
        reference_id=transfer.id,
        reference_type="CryptoTransfer",
    )
