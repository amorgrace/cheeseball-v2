import uuid

from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import BaseUserManager
from django.db import models
from django.utils import timezone


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
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = None
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    referral_code = models.CharField(max_length=20, blank=True, null=True)
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

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = CustomUserManager()

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
