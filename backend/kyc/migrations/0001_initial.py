

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("authenticator", "0007_customuser_referral_reward_paid"),
    ]

    operations = [
        migrations.CreateModel(
            name="KYCSubmission",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "id_type",
                    models.CharField(
                        choices=[
                            ("nin", "NIN"),
                            ("passport", "Passport"),
                            ("drivers_license", "Driver's license"),
                            ("voters_card", "Voter's card"),
                            ("other", "Other"),
                        ],
                        max_length=50,
                    ),
                ),
                ("document_url", models.URLField()),
                ("selfie_url", models.URLField(blank=True)),
                ("status", models.CharField(choices=[("submitted", "Submitted"), ("verified", "Verified"), ("rejected", "Rejected")], default="submitted", max_length=20)),
                ("admin_note", models.TextField(blank=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reviewed_kyc_submissions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="kyc_submissions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]

