from authenticator.auth import JWTAuth
from ninja_jwt.exceptions import AuthenticationFailed


class AdminJWTAuth(JWTAuth):
    """JWT authentication that also requires is_staff=True."""

    def __call__(self, request):
        user = super().__call__(request)
        if user is None:
            return None
        if not user.is_staff:
            raise AuthenticationFailed("Admin access required.")
        return user
