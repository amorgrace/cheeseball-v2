from ninja import Router

from .auth import JWTAuth
from .schemas import (
    LoginSchema,
    MessageSchema,
    PasswordResetChallengeSchema,
    PasswordResetConfirmSchema,
    PasswordResetRequestSchema,
    ReferralInfoSchema,
    RefreshTokenInput,
    RegisterSchema,
    ResendTokenSchema,
    TokenSchema,
    UpdateMeSchema,
    UserMeSchema,
    VerificationChallengeSchema,
    VerifyTokenSchema,
    VerifyResetTokenSchema,
)
from .views import (
    confirm_password_reset,
    get_current_user,
    get_referral_info,
    login_user,
    logout_user,
    refresh_user_token,
    register_user,
    request_password_reset,
    resend_user_token,
    update_current_user,
    verify_user_token,
    verify_reset_token,
)

router = Router(tags=["Auth"])


@router.post("/register", response=VerificationChallengeSchema)
async def register(request, payload: RegisterSchema):
    return await register_user(payload)


@router.post("/token/pair", response=TokenSchema)
async def login(request, payload: LoginSchema):
    return await login_user(request, payload)


@router.post("/token/refresh", response=TokenSchema)
async def token_refresh(request, payload: RefreshTokenInput | None = None):
    return await refresh_user_token(request, payload)


@router.post("/logout", response=MessageSchema)
async def logout(request, payload: RefreshTokenInput | None = None):
    return await logout_user(request, payload)


@router.post("/verify-token", response=TokenSchema)
async def verify_token(request, payload: VerifyTokenSchema):
    return await verify_user_token(payload)


@router.post("/verify-reset-token", response=MessageSchema)
async def verify_reset_token_endpoint(request, payload: VerifyResetTokenSchema):
    return await verify_reset_token(payload)


@router.post("/resend-token", response=VerificationChallengeSchema)
async def resend_token(request, payload: ResendTokenSchema):
    return await resend_user_token(payload)


@router.post("/forgot-password", response=PasswordResetChallengeSchema)
async def forgot_password(request, payload: PasswordResetRequestSchema):
    return await request_password_reset(payload)


@router.post("/reset-password", response=MessageSchema)
async def reset_password(request, payload: PasswordResetConfirmSchema):
    return await confirm_password_reset(payload)


@router.get("/me", response=UserMeSchema, auth=JWTAuth())
async def me(request):
    return await get_current_user(request)


@router.patch("/me", response=UserMeSchema, auth=JWTAuth())
async def update_me(request, payload: UpdateMeSchema):
    return await update_current_user(request, payload)


@router.get("/referral", response=ReferralInfoSchema, auth=JWTAuth())
async def referral(request):
    return await get_referral_info(request)


# Added for internal transfers recipient lookup
from ninja import Schema

class UserLookupResponse(Schema):
    id: str
    email: str
    fullname: str


@router.get("/users/lookup", response=UserLookupResponse, auth=JWTAuth())
async def user_lookup(request, query: str):
    from .views import lookup_user
    return await lookup_user(request, query)


