from django.db import models
from django.utils import timezone

from decimal import Decimal


class Asset(models.Model):
    WITHDRAWAL_MODE_AUTO = "auto"
    WITHDRAWAL_MODE_MANUAL = "manual"
    WITHDRAWAL_MODE_CHOICES = (
        (WITHDRAWAL_MODE_AUTO, "Automatic"),
        (WITHDRAWAL_MODE_MANUAL, "Manual Review"),
    )

    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    network = models.CharField(max_length=50, blank=True)
    binance_symbol = models.CharField(max_length=30, blank=True)
    broker_wallet_address = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    deposit_enabled = models.BooleanField(default=True)
    send_enabled = models.BooleanField(default=True)
    withdrawal_mode = models.CharField(
        max_length=10,
        choices=WITHDRAWAL_MODE_CHOICES,
        default=WITHDRAWAL_MODE_AUTO,
    )
    sort_order = models.PositiveSmallIntegerField(default=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "code"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class RateConfiguration(models.Model):
    asset = models.OneToOneField(
        Asset,
        on_delete=models.CASCADE,
        related_name="rate_configuration",
        to_field="code",
        db_column="asset",
    )
    buy_markup_percent = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("3.00"))
    sell_markup_percent = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("2.00"))
    fallback_market_rate = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("150000000.00"))
    last_market_rate = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["asset__sort_order", "asset__code"]

    def __str__(self):
        return f"{self.asset.code} rate config"


class RateQuote(models.Model):
    BUY = "buy"
    SELL = "sell"
    QUOTE_TYPES = (
        (BUY, "Buy"),
        (SELL, "Sell"),
    )

    asset = models.ForeignKey(
        Asset,
        on_delete=models.PROTECT,
        related_name="rate_quotes",
        to_field="code",
        db_column="asset",
    )
    quote_type = models.CharField(max_length=10, choices=QUOTE_TYPES)
    market_rate = models.DecimalField(max_digits=20, decimal_places=2)
    markup_percent = models.DecimalField(max_digits=6, decimal_places=2)
    final_rate = models.DecimalField(max_digits=20, decimal_places=2)
    crypto_usd_price = models.DecimalField(max_digits=20, decimal_places=8, default=Decimal("0.00000000"))
    naira_amount = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    crypto_amount = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    source = models.CharField(max_length=30, default="fallback")
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.asset.code} {self.quote_type} quote @ {self.final_rate}"

    @property
    def asset_code(self) -> str:
        return self.asset.code

    @property
    def asset_name(self) -> str:
        return self.asset.name

    @property
    def is_expired(self) -> bool:
        return self.expires_at <= timezone.now()
