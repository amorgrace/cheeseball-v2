from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from .views import _register_user_with_transaction, split_fullname


User = get_user_model()


class RegisterUserTests(TestCase):
    def test_split_fullname_separates_first_name_from_remaining_names(self):
        self.assertEqual(split_fullname("Ada Lovelace Byron"), ("Ada", "Lovelace Byron"))

    @patch("authenticator.views.send_auth_email_sync")
    def test_register_user_persists_fullname_and_phone_number(self, send_auth_email_sync):
        _register_user_with_transaction(
            email="ada@example.com",
            password="secure-pass",
            first_name="Ada",
            last_name="Lovelace",
            phone_number="+2348012345678",
            referral_code=None,
            token="123456",
            sent_at=timezone.now(),
            expires_at=timezone.now(),
        )

        user = User.objects.get(email="ada@example.com")

        self.assertEqual(user.first_name, "Ada")
        self.assertEqual(user.last_name, "Lovelace")
        self.assertEqual(user.phone_number, "+2348012345678")
        send_auth_email_sync.assert_called_once()
