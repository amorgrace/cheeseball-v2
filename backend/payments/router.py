
from ninja import Header, Router

from authenticator.auth import JWTAuth

from .schemas import (
    BankTransferSubmissionSchema,
    PaymentInstructionsSchema,
    PaymentRecordSchema,
    PaymentSetupSchema,
    PaystackWebhookSchema,
)
from .views import (
    get_payment_instructions,
    paystack_webhook,
    setup_payment,
    submit_bank_transfer,
    verify_bank_transfer,
)

router = Router(tags=["Payments"])


@router.get("/instructions", response=PaymentInstructionsSchema)
def instructions(request):
    return get_payment_instructions()


@router.post("/setup", response=PaymentRecordSchema, auth=JWTAuth())
def create_payment_setup(request, payload: PaymentSetupSchema):
    return setup_payment(request, payload)


@router.post("/transactions/{transaction_id}/bank-transfer/submit", response=PaymentRecordSchema, auth=JWTAuth())
def submit_transfer(request, transaction_id: str, payload: BankTransferSubmissionSchema):
    return submit_bank_transfer(request, transaction_id, payload)


@router.post("/admin/transactions/{transaction_id}/bank-transfer/verify", response=PaymentRecordSchema, auth=JWTAuth())
def admin_verify_transfer(request, transaction_id: str):
    return verify_bank_transfer(request, transaction_id)


@router.post("/paystack/webhook")
def webhook(
    request,
    payload: PaystackWebhookSchema,
    x_paystack_signature: str | None = Header(None, alias="x-paystack-signature"),
):
    return paystack_webhook(request, payload, x_paystack_signature)
