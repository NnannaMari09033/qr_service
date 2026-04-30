from datetime import timedelta

from rest_framework_simplejwt.tokens import Token


class Pre2FAToken(Token):
    """Short-lived token issued after password verification for users with 2FA.

    Cannot authenticate any endpoint — only valid as input to /auth/2fa/verify/,
    which exchanges it for full access/refresh tokens after a valid TOTP code.
    """
    token_type = 'pre_2fa'
    lifetime = timedelta(minutes=5)
