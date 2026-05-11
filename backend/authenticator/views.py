import logging
import hashlib
import secrets
from datetime import datetime, timedelta, timezone as dt_timezone

from anymail.exceptions import AnymailError
from asgiref.sync import sync_to_async
from django.contrib.auth import authenticate, get_user_model
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template.loader import render_to_string
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
logger = logging.getLogger(__name__)
VERIFICATION_TOKEN_TTL_MINUTES = 10
RESET_PASSWORD_TOKEN_TTL_MINUTES = 10
TOKEN_RESEND_COOLDOWN_SECONDS = 60
MAX_TOKEN_ATTEMPTS = 5


def generate_one_time_token():
    return f"{secrets.randbelow(1000000):06d}"


async def send_auth_email(*, recipient: str, subject: str, html_template: str, text_template: str, context: dict):
    text_body = render_to_string(text_template, context).strip()
    html_body = render_to_string(html_template, context)
    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        to=[recipient],
    )
    message.attach_alternative(html_body, "text/html")
    await sync_to_async(message.send)(fail_silently=False)


def send_auth_email_sync(*, recipient: str, subject: str, html_template: str, text_template: str, context: dict):
    text_body = render_to_string(text_template, context).strip()
    html_body = render_to_string(html_template, context)
    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        to=[recipient],
    )
    message.attach_alternative(html_body, "text/html")
    message.send(fail_silently=False)


def email_delivery_error_response(message: str):
    return Response({"detail": message}, status=502)


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

    first_name, last_name = split_fullname(payload.fullname)
    token = generate_one_time_token()
    sent_at = timezone.now()
    expires_at = verification_expiry()
    try:
        await sync_to_async(_register_user_with_transaction)(
            email=email,
            password=payload.password,
            first_name=first_name,
            last_name=last_name,
            phone_number=payload.phone_number,
            referral_code=payload.referral_code,
            token=token,
            sent_at=sent_at,
            expires_at=expires_at,
        )
    except AnymailError:
        logger.exception("Registration email delivery failed for %s", email)
        return email_delivery_error_response(
            "Unable to send verification email right now. Registration was rolled back. Please try again."
        )

    return {
        "message": "Registration successful. Verify your account with the code sent to your email. If you do not see it in your inbox, please check your spam or junk folder.",
        "resend_available_at": resend_available_at(sent_at).isoformat(),
    }


def split_fullname(fullname: str | None) -> tuple[str, str]:
    if not fullname:
        return "", ""

    first_name, _, last_name = fullname.strip().partition(" ")
    return first_name, last_name


def _register_user_with_transaction(
    *,
    email: str,
    password: str,
    first_name: str,
    last_name: str,
    phone_number: str | None,
    referral_code: str | None,
    token: str,
    sent_at,
    expires_at,
):
    with transaction.atomic():
        referred_by = None
        if referral_code:
            referred_by = User.objects.filter(referral_code=referral_code.strip().upper()).first()

        User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            referred_by=referred_by,
            is_active=False,
            verification_token_hash=hash_token(token),
            verification_token_expires_at=expires_at,
            verification_token_sent_at=sent_at,
        )
        send_auth_email_sync(
            subject="Verify your CheeseBall account",
            recipient=email,
            html_template="emails/verification_code.html",
            text_template="emails/verification_code.txt",
            context={
                "headline": "Verify your account",
                "preheader": "Use this code to finish setting up your CheeseBall account.",
                "intro": "Welcome to CheeseBall. Use the verification code below to activate your account.",
                "code": token,
                "expires_in_minutes": VERIFICATION_TOKEN_TTL_MINUTES,
                "action_label": "Verification code",
                "help_text": "If you did not create this account, you can safely ignore this email.",
            },
        )


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
    try:
        await send_auth_email(
            subject="Your CheeseBall verification code",
            recipient=user.email,
            html_template="emails/verification_code.html",
            text_template="emails/verification_code.txt",
            context={
                "headline": "Your new verification code",
                "preheader": "Use this fresh code to verify your CheeseBall account.",
                "intro": "Here is your new CheeseBall verification code.",
                "code": token,
                "expires_in_minutes": VERIFICATION_TOKEN_TTL_MINUTES,
                "action_label": "Verification code",
                "help_text": "If you did not request this code, you can safely ignore this email.",
            },
        )
    except AnymailError:
        logger.exception("Verification email resend failed for %s", user.email)
        return email_delivery_error_response("Unable to resend verification email right now. Please try again.")

    return {
        "message": "Verification code resent successfully. Check your email. If you do not see it in your inbox, please check your spam or junk folder.",
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
    try:
        await send_auth_email(
            subject="Reset your CheeseBall password",
            recipient=user.email,
            html_template="emails/password_reset_code.html",
            text_template="emails/password_reset_code.txt",
            context={
                "headline": "Reset your password",
                "preheader": "Use this code to reset your CheeseBall password.",
                "intro": "We received a request to reset your CheeseBall password. Use the code below to continue.",
                "code": token,
                "expires_in_minutes": RESET_PASSWORD_TOKEN_TTL_MINUTES,
                "action_label": "Reset code",
                "help_text": "If you did not request a password reset, you can ignore this email and your password will stay the same.",
            },
        )
    except AnymailError:
        logger.exception("Password reset email delivery failed for %s", user.email)
        return email_delivery_error_response("Unable to send password reset email right now. Please try again.")

    return {
        "message": "Password reset code sent successfully. Check your email. If you do not see it in your inbox, please check your spam or junk folder.",
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


REFERRAL_LINK_BASE = "https://cheeseballapp.com/register"


async def get_referral_info(request):
    user = request.auth
    referrals = await sync_to_async(list)(
        User.objects.filter(referred_by=user).values_list("email", "date_joined")
    )
    return {
        "referral_code": user.referral_code,
        "referral_link": f"{REFERRAL_LINK_BASE}?ref={user.referral_code}",
        "total_referrals": len(referrals),
        "referrals": [
            {"email": email, "joined_at": joined.isoformat()}
            for email, joined in referrals
        ],
    }
