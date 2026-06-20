import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("rates", "0008_asset_transfer_flags"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CryptoTransfer",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "sender",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sent_transfers",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "recipient",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="received_transfers",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                ("recipient_address", models.CharField(blank=True, max_length=255)),
                ("recipient_network", models.CharField(blank=True, max_length=50)),
                (
                    "asset",
                    models.ForeignKey(
                        db_column="asset",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="transfers",
                        to="rates.asset",
                        to_field="code",
                    ),
                ),
                ("amount", models.DecimalField(decimal_places=8, max_digits=30)),
                (
                    "transfer_type",
                    models.CharField(
                        choices=[("internal", "Internal (Cheeseball User)"), ("external", "External (On-Chain)")],
                        max_length=10,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("pending_review", "Pending Review"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("failure_reason", models.TextField(blank=True)),
                ("admin_notes", models.TextField(blank=True)),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reviewed_transfers",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["sender", "-created_at"], name="transfers_sender_idx"),
                    models.Index(fields=["recipient", "-created_at"], name="transfers_recipient_idx"),
                    models.Index(fields=["status", "-created_at"], name="transfers_status_idx"),
                ],
            },
        ),
    ]
