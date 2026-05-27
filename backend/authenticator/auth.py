from datetime import datetime, timezone as dt_timezone

from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from ninja_jwt.authentication import AsyncJWTAuth as BaseJWTAuth
from ninja_jwt.exceptions import AuthenticationFailed
from ninja_jwt.tokens import UntypedToken


class JWTAuth(BaseJWTAuth):
    async def __call__(self, request):
        # Prefer Authorization header, but allow HttpOnly access-token cookie.
        token = None
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1].strip()
        if not token:
            token = request.COOKIES.get("access_token")
        if not token:
            return None

        untyped_token = await sync_to_async(UntypedToken)(token)
        user_id = untyped_token.payload.get("user_id")
        if not user_id:
            raise AuthenticationFailed("Invalid token payload")

        User = get_user_model()
        user = await sync_to_async(User.objects.get)(id=user_id)
        if not user.is_active:
            raise AuthenticationFailed("User is inactive")

        if user.last_password_reset_at:
            issued_at = untyped_token.payload.get("iat")
            if issued_at:
                issued_at_dt = datetime.fromtimestamp(issued_at, tz=dt_timezone.utc)
                if issued_at_dt <= user.last_password_reset_at:
                    raise AuthenticationFailed("Token is no longer valid. Please sign in again.")

        return user

    async def authenticate(self, request, token):
        # Retain compatibility for any direct authenticate() calls.
        user = await super().authenticate(request, token)
        untyped_token = await sync_to_async(UntypedToken)(token)
        if user.last_password_reset_at:
            issued_at = untyped_token.payload.get("iat")
            if issued_at:
                issued_at_dt = datetime.fromtimestamp(issued_at, tz=dt_timezone.utc)
                if issued_at_dt <= user.last_password_reset_at:
                    raise AuthenticationFailed("Token is no longer valid. Please sign in again.")

        return user
