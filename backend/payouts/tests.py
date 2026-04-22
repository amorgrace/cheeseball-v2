from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import TestCase

from payouts.models import BeneficiaryBankAccount
from payouts.views import (
    create_beneficiary_bank_account,
    delete_beneficiary_bank_account,
    list_beneficiary_bank_accounts,
)


class BeneficiaryBankAccountTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(email="user@example.com", password="secret123")

    def make_request(self, user):
        return SimpleNamespace(auth=user)

    def test_beneficiary_accounts_can_be_created_listed_and_deleted(self):
        payload = SimpleNamespace(
            account_name="Jane Doe",
            bank_name="Demo Bank",
            account_number="0123456789",
            account_type=BeneficiaryBankAccount.SAVINGS,
        )

        created = create_beneficiary_bank_account(self.make_request(self.user), payload)
        listed = list_beneficiary_bank_accounts(self.make_request(self.user))
        response = delete_beneficiary_bank_account(self.make_request(self.user), created.id)

        self.assertEqual(created.account_name, payload.account_name)
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0].id, created.id)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(BeneficiaryBankAccount.objects.filter(id=created.id).exists())

