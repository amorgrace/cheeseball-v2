from ninja import Router
from ninja_jwt.authentication import JWTAuth

from .schemas import (
    LoginSchema,
    MessageSchema,
    RefreshTokenInput,
    RegisterSchema,
    TokenSchema,
)
from .views import login_user, logout_user, refresh_user_token, register_user

router = Router(tags=["Auth"])


@router.post("/register", response=TokenSchema)
async def register(request, payload: RegisterSchema):
    return await register_user(payload)


@router.post("/token/pair", response=TokenSchema)
async def login(request, payload: LoginSchema):
    return await login_user(request, payload)


@router.post("/token/refresh", response=TokenSchema)
async def token_refresh(request, payload: RefreshTokenInput):
    return await refresh_user_token(payload)


@router.post("/logout", response=MessageSchema, auth=JWTAuth())
async def logout(request, payload: RefreshTokenInput):
    return await logout_user(payload)
