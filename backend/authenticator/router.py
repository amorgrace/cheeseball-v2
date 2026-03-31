from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from ninja import Router, Schema
from ninja.responses import Response
from ninja_jwt.tokens import RefreshToken
from ninja_jwt.authentication import JWTAuth

from .schemas import RegisterSchema, LoginSchema, TokenSchema, MessageSchema

router = Router(tags=["Auth"])
User = get_user_model()


class RefreshTokenInput(Schema):
    refresh_token: str


@router.post("/register", response=TokenSchema)
async def register(request, payload: RegisterSchema):
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
        "message": "Registeration Successful"
    }


@router.post("/token/pair", response=TokenSchema)
async def login(request, payload: LoginSchema):
    from django.contrib.auth import authenticate

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


@router.post("/token/refresh", response=TokenSchema)
async def token_refresh(request, payload: RefreshTokenInput):
    from ninja_jwt.tokens import RefreshToken as RT

    try:
        refresh = await sync_to_async(RT)(payload.refresh_token)
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }
    except Exception:
        return Response({"detail": "Invalid or expired refresh token"}, status=401)


@router.post("/logout", response=MessageSchema, auth=JWTAuth())
async def logout(request, payload: RefreshTokenInput):
    try:
        token = await sync_to_async(RefreshToken)(payload.refresh_token)
        await sync_to_async(token.blacklist)()
        return {"message": "Logged out successfully"}
    except Exception:
        return Response({"detail": "Invalid token"}, status=400)
