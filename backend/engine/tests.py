from types import SimpleNamespace

from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model
from django.test import TestCase

from engine.admin_router import delegate_admin
from engine.admin_schemas import AdminDelegateSchema


User = get_user_model()


class AdminDelegationTests(TestCase):
    def test_delegate_admin_promotes_user_by_email(self):
        admin = User.objects.create_user(email="admin@example.com", password="secret123", is_staff=True)
        user = User.objects.create_user(email="user@example.com", password="secret123")
        request = SimpleNamespace(auth=admin)

        response = async_to_sync(delegate_admin)(request, AdminDelegateSchema(email=" USER@example.com "))

        user.refresh_from_db()
        self.assertTrue(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(response.detail, "user@example.com is now an admin.")

    def test_delegate_admin_keeps_existing_admin_unchanged(self):
        admin = User.objects.create_user(email="admin@example.com", password="secret123", is_staff=True)
        request = SimpleNamespace(auth=admin)

        response = async_to_sync(delegate_admin)(request, AdminDelegateSchema(email="admin@example.com"))

        self.assertEqual(response.detail, "admin@example.com is already an admin.")
