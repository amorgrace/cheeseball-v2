from uuid import UUID

from ninja import Router

from authenticator.auth import JWTAuth

from .schemas import BeneficiaryBankAccountCreateSchema, BeneficiaryBankAccountSchema
from .views import (
    create_beneficiary_bank_account,
    delete_beneficiary_bank_account,
    list_beneficiary_bank_accounts,
)

router = Router(tags=["Payouts"])


@router.get("/beneficiaries", response=list[BeneficiaryBankAccountSchema], auth=JWTAuth())
def beneficiaries(request):
    return list_beneficiary_bank_accounts(request)


@router.post("/beneficiaries", response=BeneficiaryBankAccountSchema, auth=JWTAuth())
def create_beneficiary(request, payload: BeneficiaryBankAccountCreateSchema):
    return create_beneficiary_bank_account(request, payload)


@router.delete("/beneficiaries/{beneficiary_id}", auth=JWTAuth())
def delete_beneficiary(request, beneficiary_id: UUID):
    return delete_beneficiary_bank_account(request, beneficiary_id)

