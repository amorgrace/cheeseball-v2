import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("authenticator", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="GiftCardSubmission",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("category", models.CharField(
                    choices=[
                        ("amazon", "Amazon"), ("itunes", "iTunes / Apple"),
                        ("google_play", "Google Play"), ("steam", "Steam"),
                        ("netflix", "Netflix"), ("xbox", "Xbox"),
                        ("playstation", "PlayStation"), ("ebay", "eBay"),
                        ("walmart", "Walmart"), ("other", "Other"),
                    ],
                    max_length=30,
                )),
                ("card_currency", models.CharField(
                    choices=[
                        ("usd", "USD"), ("gbp", "GBP"), ("eur", "EUR"),
                        ("cad", "CAD"), ("aud", "AUD"),
                    ],
                    default="usd",
                    max_length=10,
                )),
                ("declared_value", models.DecimalField(decimal_places=2, max_digits=12)),
                ("card_images", models.TextField()),
                ("card_number", models.CharField(blank=True, max_length=100)),
                ("card_pin", models.CharField(blank=True, max_length=100)),
                ("notes", models.TextField(blank=True)),
                ("status", models.CharField(
                    choices=[
                        ("pending", "Pending"),
                        ("approved", "Approved"),
                        ("rejected", "Rejected"),
                    ],
                    default="pending",
                    max_length=20,
                )),
                ("ngn_payout", models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ("admin_note", models.TextField(blank=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("reviewed_by", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="reviewed_gift_cards",
                    to="authenticator.customuser",
                )),
                ("user", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="gift_card_submissions",
                    to="authenticator.customuser",
                )),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
