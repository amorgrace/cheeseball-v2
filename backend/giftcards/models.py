import uuid

from django.conf import settings
from django.db import models


class GiftCardSubmission(models.Model):
    # ── Statuses ──────────────────────────────────────────────────────────────
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

    STATUS_CHOICES = (
        (PENDING, "Pending"),
        (APPROVED, "Approved"),
        (REJECTED, "Rejected"),
    )

    # ── Card categories ───────────────────────────────────────────────────────
    AMAZON = "amazon"
    ITUNES = "itunes"
    GOOGLE_PLAY = "google_play"
    STEAM = "steam"
    NETFLIX = "netflix"
    XBOX = "xbox"
    PLAYSTATION = "playstation"
    EBAY = "ebay"
    WALMART = "walmart"
    OTHER = "other"

    CATEGORY_CHOICES = (
        (AMAZON, "Amazon"),
        (ITUNES, "iTunes / Apple"),
        (GOOGLE_PLAY, "Google Play"),
        (STEAM, "Steam"),
        (NETFLIX, "Netflix"),
        (XBOX, "Xbox"),
        (PLAYSTATION, "PlayStation"),
        (EBAY, "eBay"),
        (WALMART, "Walmart"),
        (OTHER, "Other"),
    )

    # ── Card currencies ───────────────────────────────────────────────────────
    USD = "usd"
    GBP = "gbp"
    EUR = "eur"
    CAD = "cad"
    AUD = "aud"

    CURRENCY_CHOICES = (
        (USD, "USD"),
        (GBP, "GBP"),
        (EUR, "EUR"),
        (CAD, "CAD"),
        (AUD, "AUD"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="gift_card_submissions",
    )

    # Card details provided by the user
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    card_currency = models.CharField(max_length=10, choices=CURRENCY_CHOICES, default=USD)
    declared_value = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text="The face value of the card as declared by the user."
    )
    # One or more card images (Cloudinary URLs, comma-separated)
    card_images = models.TextField(
        help_text="Cloudinary URLs for card images, comma-separated."
    )
    card_number = models.CharField(max_length=100, blank=True)
    card_pin = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True, help_text="Optional notes from the user.")

    # Admin review
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    ngn_payout = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
        help_text="The NGN amount admin agrees to pay out."
    )
    admin_note = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="reviewed_gift_cards",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} — {self.category} ${self.declared_value} [{self.status}]"

    @property
    def card_image_list(self):
        """Return card_images as a list of URLs."""
        return [url.strip() for url in self.card_images.split(",") if url.strip()]
