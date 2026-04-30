from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken

ACCESS_COOKIE_NAME = 'access_token'
REFRESH_COOKIE_NAME = 'refresh_token'
INDICATOR_COOKIE_NAME = 'is_authenticated'


class CookieJWTAuthentication(JWTAuthentication):
    """JWT authentication that reads the access token from an HttpOnly cookie.

    The Authorization header still works (for tests, curl, third-party clients).
    A stale or invalid cookie is treated as "no auth" rather than a hard failure
    so that anonymous endpoints (login, register, landing) remain reachable.
    """

    def authenticate(self, request):
        header = self.get_header(request)
        if header is not None:
            raw_token = self.get_raw_token(header)
            if raw_token is not None:
                validated_token = self.get_validated_token(raw_token)
                return self.get_user(validated_token), validated_token

        raw_token = request.COOKIES.get(ACCESS_COOKIE_NAME)
        if raw_token is None:
            return None

        try:
            validated_token = self.get_validated_token(raw_token)
        except InvalidToken:
            return None

        return self.get_user(validated_token), validated_token
