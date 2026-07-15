import uuid

from django.conf import settings
from django.db import models


class HdWalletDerivationIndex(models.Model):
    """
    Tracks the BIP-44 derivation index assigned to a user for a given chain.
    One record per (user, chain, network) combination — acts as the canonical
    source of truth for which HD path index belongs to which user.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="hd_derivation_indexes",
    )
    chain = models.CharField(
        max_length=30,
        help_text="e.g. ethereum, bsc, polygon, celo, tron, solana",
    )
    network = models.CharField(
        max_length=50,
        blank=True,
        help_text="e.g. erc20, bep20, trc20, sol — the wallet-level label",
    )
    derivation_index = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "chain", "network")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} [{self.chain}/{self.network}] index={self.derivation_index}"


class HdWalletAddress(models.Model):
    """
    A derived deposit address for a specific user, currency and network.
    Generated deterministically from the HD wallet xpub at a fixed index.
    """

    PENDING = "pending"
    ACTIVE = "active"
    STATUS_CHOICES = (
        (PENDING, "Pending"),
        (ACTIVE, "Active"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="hd_wallet_addresses",
    )
    derivation_index = models.ForeignKey(
        HdWalletDerivationIndex,
        on_delete=models.PROTECT,
        related_name="hd_addresses",
    )
    currency = models.CharField(max_length=20, help_text="e.g. USDT, ETH, BNB")
    network = models.CharField(max_length=50, help_text="e.g. erc20, bep20, trc20, sol")
    chain = models.CharField(max_length=30, help_text="e.g. ethereum, bsc, tron, solana")
    address = models.CharField(max_length=255)
    derivation_path = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "currency", "network")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} — {self.currency}/{self.network} @ {self.address[:12]}…"


class OnChainDeposit(models.Model):
    """
    An inbound on-chain transfer detected via Tatum webhook.
    Linked optionally to a broker sell transaction.
    """

    PENDING = "pending"
    CREDITED = "credited"
    FAILED = "failed"
    STATUS_CHOICES = (
        (PENDING, "Pending"),
        (CREDITED, "Credited"),
        (FAILED, "Failed"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="on_chain_deposits",
    )
    wallet_address = models.ForeignKey(
        HdWalletAddress,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="on_chain_deposits",
    )
    broker_transaction = models.OneToOneField(
        "broker.Transaction",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="on_chain_deposit",
    )
    currency = models.CharField(max_length=20)
    network = models.CharField(max_length=50, blank=True)
    amount = models.DecimalField(max_digits=30, decimal_places=8)
    txid = models.CharField(max_length=255, blank=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    tatum_subscription_id = models.CharField(max_length=255, blank=True, db_index=True)
    provider_payload = models.JSONField(default=dict, blank=True)
    credited_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "currency", "status"]),
            models.Index(fields=["txid", "currency"]),
        ]

    def __str__(self):
        return f"{self.user.email} — {self.amount} {self.currency} [{self.status}]"


class OnChainWithdrawal(models.Model):
    """
    An outbound on-chain withdrawal broadcast by the signer service.
    """

    PENDING = "pending"
    BROADCAST = "broadcast"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    STATUS_CHOICES = (
        (PENDING, "Pending"),
        (BROADCAST, "Broadcast"),
        (CONFIRMED, "Confirmed"),
        (FAILED, "Failed"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="on_chain_withdrawals",
    )
    currency = models.CharField(max_length=20)
    network = models.CharField(max_length=50, blank=True)
    chain = models.CharField(max_length=30, blank=True)
    amount = models.DecimalField(max_digits=30, decimal_places=8)
    to_address = models.CharField(max_length=255)
    txid = models.CharField(max_length=255, blank=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    signer_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} — withdraw {self.amount} {self.currency} → {self.to_address[:12]}…"
