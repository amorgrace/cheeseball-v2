from datetime import datetime, timezone as dt_timezone

from asgiref.sync import sync_to_async
from ninja_jwt.authentication import AsyncJWTAuth as BaseJWTAuth
from ninja_jwt.exceptions import AuthenticationFailed
from ninja_jwt.tokens import UntypedToken


class JWTAuth(BaseJWTAuth):
    async def authenticate(self, request, token):
        user = await super().authenticate(request, token)
        untyped_token = await sync_to_async(UntypedToken)(token)

        if user.last_password_reset_at:
            issued_at = untyped_token.payload.get("iat")
            if issued_at:
                issued_at_dt = datetime.fromtimestamp(issued_at, tz=dt_timezone.utc)
                if issued_at_dt <= user.last_password_reset_at:
                    raise AuthenticationFailed("Token is no longer valid. Please sign in again.")

        return user
