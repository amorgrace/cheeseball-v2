import json
import logging
import uuid
from decimal import ROUND_HALF_UP
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


def _paystack_headers() -> dict:
    if not settings.PAYSTACK_SECRET_KEY:
        raise ValidationError("Paystack secret key is not configured")
    return {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
        "User-Agent": "CheeseBall/1.0 (+https://cheeseballapp.com)",
    }


def _amount_to_kobo(amount) -> int:
    return int((amount * 100).quantize(0, rounding=ROUND_HALF_UP))


def create_transfer_recipient(*, account_name: str, account_number: str, bank_code: str) -> dict:
    """
    Creates a Paystack Transfer Recipient for a Nigerian bank account.
    Returns the full Paystack response including the recipient_code.
    """
    payload = {
        "type": "nuban",
        "name": account_name,
        "account_number": account_number,
        "bank_code": bank_code,
        "currency": settings.PAYSTACK_CURRENCY,
    }
    request = Request(
        settings.PAYSTACK_TRANSFER_RECIPIENT_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers=_paystack_headers(),
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise ValidationError(f"Paystack create recipient failed: {error_body}") from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ValidationError("Unable to create Paystack transfer recipient") from exc

    if not result.get("status"):
        raise ValidationError(result.get("message") or "Paystack create recipient failed")
    return result


def initiate_transfer(*, recipient_code: str, amount_naira, reason: str = "", reference: str | None = None) -> dict:
    """
    Initiates a Paystack Transfer (outgoing NGN payout) to a transfer recipient.
    Returns the full Paystack response including the transfer_code.
    """
    payload = {
        "source": "balance",
        "amount": str(_amount_to_kobo(amount_naira)),
        "recipient": recipient_code,
        "reason": reason or "CheeseBall sell payout",
        "reference": reference or f"cb-sell-{uuid.uuid4().hex[:16]}",
        "currency": settings.PAYSTACK_CURRENCY,
    }
    request = Request(
        settings.PAYSTACK_TRANSFER_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers=_paystack_headers(),
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise ValidationError(f"Paystack transfer failed: {error_body}") from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ValidationError("Unable to initiate Paystack transfer") from exc

    if not result.get("status"):
        raise ValidationError(result.get("message") or "Paystack transfer failed")
    return result


def process_sell_payout(transaction) -> dict:
    """
    End-to-end payout for a sell transaction via Paystack Transfers.
    1. Creates a transfer recipient from the transaction's bank details
    2. Initiates the transfer
    Returns the Paystack transfer response.
    """
    if not transaction.bank_account_number or not transaction.bank_name:
        raise ValidationError("Transaction is missing bank account details for payout")

    bank_code = getattr(transaction, "_bank_code", None) or ""
    if not bank_code:
        # Try to look up the bank_code from the beneficiary record
        from payouts.models import BeneficiaryBankAccount
        beneficiary = BeneficiaryBankAccount.objects.filter(
            user=transaction.user,
            bank_name=transaction.bank_name,
            account_number=transaction.bank_account_number,
        ).first()
        if beneficiary and beneficiary.bank_code:
            bank_code = beneficiary.bank_code
        else:
            raise ValidationError(
                f"Bank code not found for {transaction.bank_name}. "
                "Please update the beneficiary with a valid Paystack bank code."
            )

    recipient_response = create_transfer_recipient(
        account_name=transaction.bank_account_name,
        account_number=transaction.bank_account_number,
        bank_code=bank_code,
    )
    recipient_code = recipient_response.get("data", {}).get("recipient_code")
    if not recipient_code:
        raise ValidationError("Paystack did not return a recipient_code")

    transfer_response = initiate_transfer(
        recipient_code=recipient_code,
        amount_naira=transaction.naira_amount,
        reason=f"CheeseBall sell payout for {transaction.id}",
    )
    logger.info("Paystack sell payout initiated for transaction %s", transaction.id)
    return transfer_response
