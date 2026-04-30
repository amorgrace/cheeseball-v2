import secrets
import string
import uuid

from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import BaseUserManager
from django.db import models
from django.utils import timezone

REFERRAL_CODE_LENGTH = 6
REFERRAL_CODE_PREFIX = "CB"


def generate_referral_code():
    alphabet = string.ascii_uppercase + string.digits
    while True:
        suffix = "".join(secrets.choice(alphabet) for _ in range(REFERRAL_CODE_LENGTH))
        code = f"{REFERRAL_CODE_PREFIX}{suffix}"
        if not CustomUser.objects.filter(referral_code=code).exists():
            return code


class CustomUserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")

        email = self.normalize_email(email).strip().lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    KYC_UNVERIFIED = "unverified"
    KYC_SUBMITTED = "submitted"
    KYC_VERIFIED = "verified"
    KYC_REJECTED = "rejected"
    KYC_STATUS_CHOICES = (
        (KYC_UNVERIFIED, "Unverified"),
        (KYC_SUBMITTED, "Submitted"),
        (KYC_VERIFIED, "Verified"),
        (KYC_REJECTED, "Rejected"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = None
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    referral_code = models.CharField(max_length=10, unique=True, blank=True)
    referred_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="referrals",
    )
    verification_token_hash = models.CharField(max_length=64, blank=True, null=True)
    verification_token_expires_at = models.DateTimeField(blank=True, null=True)
    verification_token_sent_at = models.DateTimeField(blank=True, null=True)
    verification_failed_attempts = models.PositiveSmallIntegerField(default=0)
    verified_at = models.DateTimeField(blank=True, null=True)
    reset_password_token_hash = models.CharField(max_length=64, blank=True, null=True)
    reset_password_token_expires_at = models.DateTimeField(blank=True, null=True)
    reset_password_token_sent_at = models.DateTimeField(blank=True, null=True)
    reset_password_failed_attempts = models.PositiveSmallIntegerField(default=0)
    last_password_reset_at = models.DateTimeField(blank=True, null=True)
    referral_reward_paid = models.BooleanField(default=False)
    kyc_status = models.CharField(max_length=20, choices=KYC_STATUS_CHOICES, default=KYC_UNVERIFIED)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = CustomUserManager()

    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = generate_referral_code()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email

    @property
    def has_valid_verification_token(self):
        return bool(
            self.verification_token_hash
            and self.verification_token_expires_at
            and self.verification_token_expires_at > timezone.now()
        )

    @property
    def has_valid_reset_password_token(self):
        return bool(
            self.reset_password_token_hash
            and self.reset_password_token_expires_at
            and self.reset_password_token_expires_at > timezone.now()
        )
