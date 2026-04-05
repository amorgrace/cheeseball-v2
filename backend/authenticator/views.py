import hashlib
import secrets
from datetime import datetime, timedelta, timezone as dt_timezone

from asgiref.sync import sync_to_async
from django.contrib.auth import authenticate, get_user_model
from django.utils import timezone
from ninja.responses import Response
from ninja_jwt.tokens import RefreshToken

from .schemas import (
    LoginSchema,
    PasswordResetConfirmSchema,
    PasswordResetRequestSchema,
    RefreshTokenInput,
    RegisterSchema,
    ResendTokenSchema,
    UpdateMeSchema,
    VerifyTokenSchema,
)

User = get_user_model()
VERIFICATION_TOKEN_TTL_MINUTES = 10
RESET_PASSWORD_TOKEN_TTL_MINUTES = 10
TOKEN_RESEND_COOLDOWN_SECONDS = 60
MAX_TOKEN_ATTEMPTS = 5


def generate_one_time_token():
    return f"{secrets.randbelow(1000000):06d}"


def normalize_email(email: str) -> str:
    return email.strip().lower()


def verification_expiry():
    return timezone.now() + timedelta(minutes=VERIFICATION_TOKEN_TTL_MINUTES)


def reset_password_expiry():
    return timezone.now() + timedelta(minutes=RESET_PASSWORD_TOKEN_TTL_MINUTES)


def resend_available_at(sent_at):
    return sent_at + timedelta(seconds=TOKEN_RESEND_COOLDOWN_SECONDS)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def token_matches(raw_token: str, stored_hash: str | None) -> bool:
    if not stored_hash:
        return False
    return secrets.compare_digest(hash_token(raw_token), stored_hash)


def format_dt(value):
    return value.isoformat() if value else None


def is_resend_blocked(sent_at):
    return bool(sent_at and resend_available_at(sent_at) > timezone.now())


def is_token_issued_before_password_reset(token, user) -> bool:
    if not user.last_password_reset_at:
        return False

    issued_at = token.payload.get("iat")
    if not issued_at:
        return False

    issued_at_dt = datetime.fromtimestamp(issued_at, tz=dt_timezone.utc)
    return issued_at_dt <= user.last_password_reset_at


async def register_user(payload: RegisterSchema):
    email = normalize_email(payload.email)
    if await User.objects.filter(email=email).aexists():
        return Response({"detail": "Email already registered"}, status=400)

    token = generate_one_time_token()
    sent_at = timezone.now()
    expires_at = verification_expiry()
    await sync_to_async(User.objects.create_user)(
        email=email,
        password=payload.password,
        referral_code=payload.referral_code,
        is_active=False,
        verification_token_hash=hash_token(token),
        verification_token_expires_at=expires_at,
        verification_token_sent_at=sent_at,
    )

    return {
        "message": "Registration successful. Verify your account with the token sent.",
        "verification_token": token,
        "verification_token_expires_at": expires_at.isoformat(),
        "resend_available_at": resend_available_at(sent_at).isoformat(),
    }


async def login_user(request, payload: LoginSchema):
    email = normalize_email(payload.email)
    existing_user = await User.objects.filter(email=email).afirst()
    password_matches = bool(existing_user and await sync_to_async(existing_user.check_password)(payload.password))
    if existing_user and password_matches and not existing_user.is_active:
        return Response({"detail": "Account not verified. Please verify your account first."}, status=403)

    user = await sync_to_async(authenticate)(
        request,
        username=email,
        password=payload.password,
    )
    if not user:
        return Response({"detail": "Invalid credentials"}, status=401)

    refresh = await sync_to_async(RefreshToken.for_user)(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "message": "Login successful",
    }


async def refresh_user_token(payload: RefreshTokenInput):
    try:
        refresh = await sync_to_async(RefreshToken)(payload.refresh_token)
        user = await User.objects.aget(id=refresh.payload["user_id"])
        if is_token_issued_before_password_reset(refresh, user):
            return Response({"detail": "Invalid or expired refresh token"}, status=401)
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }
    except Exception:
        return Response({"detail": "Invalid or expired refresh token"}, status=401)


async def logout_user(payload: RefreshTokenInput):
    try:
        token = await sync_to_async(RefreshToken)(payload.refresh_token)
        await sync_to_async(token.blacklist)()
        return {"message": "Logged out successfully"}
    except Exception:
        return Response({"detail": "Invalid token"}, status=400)


async def verify_user_token(payload: VerifyTokenSchema):
    user = await User.objects.filter(email=normalize_email(payload.email)).afirst()
    if not user:
        return Response({"detail": "User not found"}, status=404)

    if user.is_active:
        refresh = await sync_to_async(RefreshToken.for_user)(user)
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "message": "Account already verified",
        }

    if user.verification_failed_attempts >= MAX_TOKEN_ATTEMPTS:
        return Response({"detail": "Too many invalid verification attempts. Please request a new token."}, status=429)

    if not token_matches(payload.token, user.verification_token_hash):
        user.verification_failed_attempts += 1
        await sync_to_async(user.save)(update_fields=["verification_failed_attempts"])
        return Response({"detail": "Invalid verification token"}, status=400)

    if not user.has_valid_verification_token:
        return Response({"detail": "Verification token expired"}, status=400)

    user.is_active = True
    user.verified_at = timezone.now()
    user.verification_token_hash = None
    user.verification_token_expires_at = None
    user.verification_token_sent_at = None
    user.verification_failed_attempts = 0
    await sync_to_async(user.save)(
        update_fields=[
            "is_active",
            "verified_at",
            "verification_token_hash",
            "verification_token_expires_at",
            "verification_token_sent_at",
            "verification_failed_attempts",
        ]
    )

    refresh = await sync_to_async(RefreshToken.for_user)(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "message": "Account verified successfully",
    }


async def resend_user_token(payload: ResendTokenSchema):
    user = await User.objects.filter(email=normalize_email(payload.email)).afirst()
    if not user:
        return Response({"detail": "User not found"}, status=404)

    if user.is_active:
        return Response({"detail": "Account already verified"}, status=400)

    if is_resend_blocked(user.verification_token_sent_at):
        return Response({"detail": "Please wait before requesting another verification token."}, status=429)

    token = generate_one_time_token()
    sent_at = timezone.now()
    expires_at = verification_expiry()
    user.verification_token_hash = hash_token(token)
    user.verification_token_expires_at = expires_at
    user.verification_token_sent_at = sent_at
    user.verification_failed_attempts = 0
    await sync_to_async(user.save)(
        update_fields=[
            "verification_token_hash",
            "verification_token_expires_at",
            "verification_token_sent_at",
            "verification_failed_attempts",
        ]
    )

    return {
        "message": "Verification token resent successfully",
        "verification_token": token,
        "verification_token_expires_at": expires_at.isoformat(),
        "resend_available_at": resend_available_at(sent_at).isoformat(),
    }


async def request_password_reset(payload: PasswordResetRequestSchema):
    user = await User.objects.filter(email=normalize_email(payload.email)).afirst()
    if not user:
        return Response({"detail": "User not found"}, status=404)

    if is_resend_blocked(user.reset_password_token_sent_at):
        return Response({"detail": "Please wait before requesting another reset token."}, status=429)

    token = generate_one_time_token()
    sent_at = timezone.now()
    expires_at = reset_password_expiry()
    user.reset_password_token_hash = hash_token(token)
    user.reset_password_token_expires_at = expires_at
    user.reset_password_token_sent_at = sent_at
    user.reset_password_failed_attempts = 0
    await sync_to_async(user.save)(
        update_fields=[
            "reset_password_token_hash",
            "reset_password_token_expires_at",
            "reset_password_token_sent_at",
            "reset_password_failed_attempts",
        ]
    )

    return {
        "message": "Password reset token generated successfully",
        "reset_token": token,
        "reset_token_expires_at": expires_at.isoformat(),
        "resend_available_at": resend_available_at(sent_at).isoformat(),
    }


async def confirm_password_reset(payload: PasswordResetConfirmSchema):
    user = await User.objects.filter(email=normalize_email(payload.email)).afirst()
    if not user:
        return Response({"detail": "User not found"}, status=404)

    if user.reset_password_failed_attempts >= MAX_TOKEN_ATTEMPTS:
        return Response({"detail": "Too many invalid reset attempts. Please request a new token."}, status=429)

    if not token_matches(payload.token, user.reset_password_token_hash):
        user.reset_password_failed_attempts += 1
        await sync_to_async(user.save)(update_fields=["reset_password_failed_attempts"])
        return Response({"detail": "Invalid reset token"}, status=400)

    if not user.has_valid_reset_password_token:
        return Response({"detail": "Reset token expired"}, status=400)

    await sync_to_async(user.set_password)(payload.password)
    user.reset_password_token_hash = None
    user.reset_password_token_expires_at = None
    user.reset_password_token_sent_at = None
    user.reset_password_failed_attempts = 0
    user.last_password_reset_at = timezone.now()
    await sync_to_async(user.save)(
        update_fields=[
            "password",
            "reset_password_token_hash",
            "reset_password_token_expires_at",
            "reset_password_token_sent_at",
            "reset_password_failed_attempts",
            "last_password_reset_at",
        ]
    )

    return {"message": "Password reset successful"}


async def get_current_user(request):
    user = request.auth
    return {
        "id": user.id,
        "email": user.email,
        "phone_number": user.phone_number,
        "referral_code": user.referral_code,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_staff": user.is_staff,
        "verified_at": format_dt(user.verified_at),
    }


async def update_current_user(request, payload: UpdateMeSchema):
    user = request.auth
    update_fields = []

    for field in ("first_name", "last_name", "phone_number"):
        value = getattr(payload, field)
        if value is not None:
            setattr(user, field, value.strip() if isinstance(value, str) else value)
            update_fields.append(field)

    if update_fields:
        await sync_to_async(user.save)(update_fields=update_fields)

    return await get_current_user(request)
