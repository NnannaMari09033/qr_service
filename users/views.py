import io
import base64

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth.models import User
from django_otp.plugins.otp_totp.models import TOTPDevice
from drf_spectacular.utils import extend_schema

from .serializers import UserSerializer, RegisterSerializer

import qrcode as qrcode_lib


class RegisterView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(summary="Register a new user", request=RegisterSerializer, responses={201: UserSerializer})
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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

    @extend_schema(summary="Delete your account", responses={204: None})
    def delete(self, request):
        request.user.delete()
        return Response(
            {'message': 'Account deleted successfully'},
            status=status.HTTP_204_NO_CONTENT
        )


class Setup2FAView(APIView):
    """Generate a TOTP secret and return a QR code for authenticator apps."""
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Set up 2FA — get QR code")
    def post(self, request):
        # Remove any unconfirmed devices
        TOTPDevice.objects.filter(user=request.user, confirmed=False).delete()

        # Create new unconfirmed device
        device = TOTPDevice.objects.create(
            user=request.user,
            name='Authenticator App',
            confirmed=False,
        )

        # Build otpauth URI
        otp_uri = device.config_url

        # Generate QR code as base64 PNG
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
                status=status.HTTP_400_BAD_REQUEST
            )

        if device.verify_token(code):
            device.confirmed = True
            device.save()
            return Response({'message': '2FA enabled successfully'}, status=status.HTTP_200_OK)

        return Response(
            {'error': 'Invalid code. Please try again.'},
            status=status.HTTP_400_BAD_REQUEST
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
                status=status.HTTP_400_BAD_REQUEST
            )

        if not device.verify_token(code):
            return Response(
                {'error': 'Invalid code'},
                status=status.HTTP_400_BAD_REQUEST
            )

        TOTPDevice.objects.filter(user=request.user).delete()
        return Response({'message': '2FA disabled'}, status=status.HTTP_200_OK)


class Verify2FAView(APIView):
    """Verify a TOTP code during login (called after password auth)."""
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Verify 2FA code during login")
    def post(self, request):
        code = request.data.get('code', '')
        device = TOTPDevice.objects.filter(user=request.user, confirmed=True).first()

        if not device:
            return Response({'verified': True, 'message': '2FA not enabled'}, status=status.HTTP_200_OK)

        if device.verify_token(code):
            return Response({'verified': True}, status=status.HTTP_200_OK)

        return Response(
            {'verified': False, 'error': 'Invalid 2FA code'},
            status=status.HTTP_400_BAD_REQUEST
        )