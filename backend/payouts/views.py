from uuid import UUID

from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from ninja.responses import Response

from .models import BeneficiaryBankAccount


def create_beneficiary_bank_account(request, payload):
    try:
        return BeneficiaryBankAccount.objects.create(
            user=request.auth,
            account_name=payload.account_name.strip(),
            bank_name=payload.bank_name.strip(),
            account_number=payload.account_number.strip(),
            account_type=payload.account_type,
        )
    except IntegrityError:
        return Response({"detail": "Beneficiary bank account already exists"}, status=400)


def list_beneficiary_bank_accounts(request):
    return list(BeneficiaryBankAccount.objects.filter(user=request.auth))


def delete_beneficiary_bank_account(request, beneficiary_id: UUID):
    beneficiary = get_object_or_404(BeneficiaryBankAccount, id=beneficiary_id, user=request.auth)
    beneficiary.delete()
    return Response({}, status=204)

