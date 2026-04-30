import io
import base64

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django_otp.plugins.otp_totp.models import TOTPDevice
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

import qrcode as qrcode_lib

from .authentication import (
    ACCESS_COOKIE_NAME,
    INDICATOR_COOKIE_NAME,
    REFRESH_COOKIE_NAME,
)
from .serializers import RegisterSerializer, UserSerializer
from .throttles import LoginRateThrottle
from .tokens import Pre2FAToken


def _set_auth_cookies(response, access_token, refresh_token):
    secure = not settings.DEBUG
    access_max_age = int(settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds())
    refresh_max_age = int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds())

    response.set_cookie(
        ACCESS_COOKIE_NAME, str(access_token),
        max_age=access_max_age, httponly=True, secure=secure, samesite='Lax', path='/',
    )
    response.set_cookie(
        REFRESH_COOKIE_NAME, str(refresh_token),
        max_age=refresh_max_age, httponly=True, secure=secure, samesite='Lax', path='/auth/',
    )
    response.set_cookie(
        INDICATOR_COOKIE_NAME, '1',
        max_age=refresh_max_age, httponly=False, secure=secure, samesite='Lax', path='/',
    )


def _clear_auth_cookies(response):
    response.delete_cookie(ACCESS_COOKIE_NAME, path='/')
    response.delete_cookie(REFRESH_COOKIE_NAME, path='/auth/')
    response.delete_cookie(INDICATOR_COOKIE_NAME, path='/')


class RegisterView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(summary="Register a new user", request=RegisterSerializer, responses={201: UserSerializer})
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    """Verify username/password.

    If the user has 2FA enabled, returns a short-lived pre_auth_token in the body
    (no auth cookies set). The client must call /auth/2fa/verify/ with that token
    plus a valid TOTP code to receive real access/refresh cookies.

    Otherwise, sets HttpOnly access/refresh cookies and an is_authenticated indicator.
    """
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    @extend_schema(summary="Log in with username and password")
    def post(self, request):
        username = request.data.get('username', '')
        password = request.data.get('password', '')

        user = authenticate(username=username, password=password)
        if user is None or not user.is_active:
            return Response(
                {'detail': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        has_2fa = TOTPDevice.objects.filter(user=user, confirmed=True).exists()

        if has_2fa:
            pre_token = Pre2FAToken.for_user(user)
            return Response(
                {'requires_2fa': True, 'pre_auth_token': str(pre_token)},
                status=status.HTTP_200_OK,
            )

        refresh = RefreshToken.for_user(user)
        response = Response({'requires_2fa': False}, status=status.HTTP_200_OK)
        _set_auth_cookies(response, refresh.access_token, refresh)
        return response


class CookieRefreshView(APIView):
    """Read refresh token from cookie, issue new access (and rotated refresh) cookies."""
    permission_classes = [AllowAny]

    @extend_schema(summary="Refresh access token from cookie")
    def post(self, request):
        raw_refresh = request.COOKIES.get(REFRESH_COOKIE_NAME)
        if not raw_refresh:
            return Response({'detail': 'No refresh token'}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = TokenRefreshSerializer(data={'refresh': raw_refresh})
        try:
            serializer.is_valid(raise_exception=True)
        except (InvalidToken, TokenError):
            response = Response({'detail': 'Invalid refresh token'}, status=status.HTTP_401_UNAUTHORIZED)
            _clear_auth_cookies(response)
            return response

        access = serializer.validated_data['access']
        new_refresh = serializer.validated_data.get('refresh', raw_refresh)

        response = Response(status=status.HTTP_200_OK)
        _set_auth_cookies(response, access, new_refresh)
        return response


class LogoutView(APIView):
    """Blacklist the refresh token (if present) and clear all auth cookies."""
    permission_classes = [AllowAny]

    @extend_schema(summary="Log out and clear auth cookies")
    def post(self, request):
        raw_refresh = request.COOKIES.get(REFRESH_COOKIE_NAME)
        if raw_refresh:
            try:
                RefreshToken(raw_refresh).blacklist()
            except (TokenError, AttributeError):
                pass

        response = Response(status=status.HTTP_204_NO_CONTENT)
        _clear_auth_cookies(response)
        return response


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Get your profile", responses={200: UserSerializer})
    def get(self, request):
        serializer = UserSerializer(request.user)
        has_2fa = TOTPDevice.objects.filter(user=request.user, confirmed=True).exists()
        data = serializer.data
        data['has_2fa'] = has_2fa
        return Response(data, status=status.HTTP_200_OK)

    @extend_schema(summary="Update your profile", request=UserSerializer, responses={200: UserSerializer})
    def put(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(summary="Delete your account (requires password and TOTP if 2FA enabled)")
    def delete(self, request):
        password = request.data.get('password', '')
        if not password or not request.user.check_password(password):
            return Response(
                {'error': 'Invalid password'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        device = TOTPDevice.objects.filter(user=request.user, confirmed=True).first()
        if device is not None:
            code = request.data.get('totp_code', '')
            if not code or not device.verify_token(code):
                return Response(
                    {'error': 'Invalid 2FA code'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        request.user.delete()
        response = Response(status=status.HTTP_204_NO_CONTENT)
        _clear_auth_cookies(response)
        return response


class Setup2FAView(APIView):
    """Generate a TOTP secret and return a QR code for authenticator apps."""
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Set up 2FA — get QR code")
    def post(self, request):
        TOTPDevice.objects.filter(user=request.user, confirmed=False).delete()

        device = TOTPDevice.objects.create(
            user=request.user,
            name='Authenticator App',
            confirmed=False,
        )

        otp_uri = device.config_url
        img = qrcode_lib.make(otp_uri)
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()

        return Response({
            'qr_code': f'data:image/png;base64,{qr_base64}',
            'secret': device.key,
            'device_id': device.persistent_id,
        }, status=status.HTTP_200_OK)


class Confirm2FAView(APIView):
    """Verify a TOTP code to confirm 2FA setup."""
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Confirm 2FA setup with a code from your authenticator")
    def post(self, request):
        code = request.data.get('code', '')
        device = TOTPDevice.objects.filter(user=request.user, confirmed=False).first()

        if not device:
            return Response(
                {'error': '2FA setup not started. Call setup first.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if device.verify_token(code):
            device.confirmed = True
            device.save()
            return Response({'message': '2FA enabled successfully'}, status=status.HTTP_200_OK)

        return Response(
            {'error': 'Invalid code. Please try again.'},
            status=status.HTTP_400_BAD_REQUEST,
        )


class Disable2FAView(APIView):
    """Disable 2FA for the authenticated user."""
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Disable 2FA")
    def post(self, request):
        code = request.data.get('code', '')
        device = TOTPDevice.objects.filter(user=request.user, confirmed=True).first()

        if not device:
            return Response(
                {'error': '2FA is not enabled'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not device.verify_token(code):
            return Response(
                {'error': 'Invalid code'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        TOTPDevice.objects.filter(user=request.user).delete()
        return Response({'message': '2FA disabled'}, status=status.HTTP_200_OK)


class Verify2FAView(APIView):
    """Exchange a Pre2FA token + TOTP code for full access/refresh cookies.

    This is the second step of the 2FA login flow. The client receives a
    pre_auth_token from /auth/login/ when the user has 2FA enabled; that
    token is useless on its own and only valid as input to this endpoint.
    """
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    @extend_schema(summary="Verify 2FA code during login")
    def post(self, request):
        raw_pre_token = request.data.get('pre_auth_token')
        code = request.data.get('code', '')

        if not raw_pre_token:
            return Response(
                {'error': 'pre_auth_token is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            pre_token = Pre2FAToken(raw_pre_token)
        except TokenError:
            return Response(
                {'error': 'Invalid or expired login session'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            user = User.objects.get(pk=pre_token['user_id'])
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.is_active:
            return Response(
                {'error': 'Account is disabled'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        device = TOTPDevice.objects.filter(user=user, confirmed=True).first()
        if not device:
            return Response(
                {'error': '2FA is not enabled on this account'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not device.verify_token(code):
            return Response(
                {'error': 'Invalid 2FA code'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        refresh = RefreshToken.for_user(user)
        response = Response({'verified': True}, status=status.HTTP_200_OK)
        _set_auth_cookies(response, refresh.access_token, refresh)
        return response
