import json
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import TestCase

from kyc.models import KYCSubmission
from kyc.views import approve, reject, submit_submission


class KYCFlowTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(email="user@example.com", password="secret123")
        self.admin = user_model.objects.create_user(
            email="admin@example.com",
            password="secret123",
            is_staff=True,
        )

    def make_request(self, user):
        return SimpleNamespace(auth=user)

    def test_submit_sets_submitted_status(self):
        payload = SimpleNamespace(
            id_type="passport",
            document_url="https://res.cloudinary.com/demo/image/upload/v1/id.png",
        )

        result = submit_submission(self.make_request(self.user), payload)
        self.user.refresh_from_db()

        self.assertEqual(result["status"], KYCSubmission.SUBMITTED)
        self.assertEqual(self.user.kyc_status, self.user.KYC_SUBMITTED)

    def test_resubmit_is_blocked_before_rejection(self):
        payload = SimpleNamespace(
            id_type="nin",
            document_url="https://res.cloudinary.com/demo/image/upload/v1/id-1.png",
        )
        submit_submission(self.make_request(self.user), payload)

        response = submit_submission(self.make_request(self.user), payload)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            json.loads(response.content)["detail"],
            "['You can only submit KYC again after rejection']",
        )

    def test_resubmit_allowed_after_rejection(self):
        payload = SimpleNamespace(
            id_type="nin",
            document_url="https://res.cloudinary.com/demo/image/upload/v1/id-1.png",
        )
        first = submit_submission(self.make_request(self.user), payload)
        reject(
            self.make_request(self.admin),
            first["id"],
            SimpleNamespace(reason="Image is blurred"),
        )

        second = submit_submission(
            self.make_request(self.user),
            SimpleNamespace(
                id_type="passport",
                document_url="https://res.cloudinary.com/demo/image/upload/v1/id-2.png",
            ),
        )
        self.assertEqual(second["status"], KYCSubmission.SUBMITTED)

    def test_admin_approve_marks_user_verified(self):
        payload = SimpleNamespace(
            id_type="passport",
            document_url="https://res.cloudinary.com/demo/image/upload/v1/id.png",
        )
        submitted = submit_submission(self.make_request(self.user), payload)

        result = approve(
            self.make_request(self.admin),
            submitted["id"],
            SimpleNamespace(note="Looks valid"),
        )
        self.user.refresh_from_db()

        self.assertEqual(result["status"], KYCSubmission.VERIFIED)
        self.assertEqual(self.user.kyc_status, self.user.KYC_VERIFIED)

