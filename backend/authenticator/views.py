from asgiref.sync import sync_to_async
from django.contrib.auth import authenticate, get_user_model
from ninja.responses import Response
from ninja_jwt.tokens import RefreshToken

from .schemas import LoginSchema, RefreshTokenInput, RegisterSchema

User = get_user_model()


async def register_user(payload: RegisterSchema):
    if await User.objects.filter(email=payload.email).aexists():
        return Response({"detail": "Email already registered"}, status=400)

    user = await sync_to_async(User.objects.create_user)(
        email=payload.email,
        password=payload.password,
        referral_code=payload.referral_code,
    )

    refresh = await sync_to_async(RefreshToken.for_user)(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "message": "Registration successful",
    }


async def login_user(request, payload: LoginSchema):
    user = await sync_to_async(authenticate)(
        request,
        username=payload.email,
        password=payload.password,
    )
    if not user:
        return Response({"detail": "Invalid credentials"}, status=401)

    refresh = await sync_to_async(RefreshToken.for_user)(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


async def refresh_user_token(payload: RefreshTokenInput):
    try:
        refresh = await sync_to_async(RefreshToken)(payload.refresh_token)
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
