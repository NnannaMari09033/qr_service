import os
from urllib.parse import urlparse

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.shortcuts import redirect
from django.http import FileResponse, Http404
from django.conf import settings
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .models import QRCode
from .serializers import QRCodeSerializer
from .services.qr_service import generate_qr_code
from analytics.models import Scan


class CreateQRInputSerializer(serializers.Serializer):
    """Tells Swagger what the POST /qr/ body looks like."""
    original_url = serializers.URLField()


class QRCodeListView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="List your QR codes",
        responses={200: QRCodeSerializer(many=True)},
    )
    def get(self, request):
        if request.user.is_authenticated:
            qr_codes = QRCode.objects.filter(owner=request.user)
        else:
            qr_codes = QRCode.objects.none()
        serializer = QRCodeSerializer(qr_codes, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Create a new QR code",
        request=CreateQRInputSerializer,
        responses={201: QRCodeSerializer},
    )
    def post(self, request):
        original_url = request.data.get('original_url')

        if not original_url:
            return Response(
                {'error': 'original_url is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        parsed = urlparse(original_url)
        if parsed.scheme not in ('http', 'https'):
            return Response(
                {'error': 'Only http and https URLs are allowed'},
                status=status.HTTP_400_BAD_REQUEST
            )

        owner = request.user if request.user.is_authenticated else None
        qr_code = generate_qr_code(original_url, owner=owner, request=request)
        serializer = QRCodeSerializer(qr_code)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class QRCodeDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_qr_code(self, short_code, user):
        try:
            qr_code = QRCode.objects.get(short_code=short_code, owner=user)
        except QRCode.DoesNotExist:
            return None
        return qr_code

    @extend_schema(summary="Get QR code details", responses={200: QRCodeSerializer})
    def get(self, request, short_code):
        qr_code = self.get_qr_code(short_code, request.user)
        if not qr_code:
            return Response(
                {'error': 'QR code not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = QRCodeSerializer(qr_code)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Update QR code URL",
        request=CreateQRInputSerializer,
        responses={200: QRCodeSerializer},
    )
    def put(self, request, short_code):
        qr_code = self.get_qr_code(short_code, request.user)
        if not qr_code:
            return Response(
                {'error': 'QR code not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        original_url = request.data.get('original_url')
        if not original_url:
            return Response(
                {'error': 'original_url is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        parsed = urlparse(original_url)
        if parsed.scheme not in ('http', 'https'):
            return Response(
                {'error': 'Only http and https URLs are allowed'},
                status=status.HTTP_400_BAD_REQUEST
            )

        qr_code.original_url = original_url
        qr_code.save()
        serializer = QRCodeSerializer(qr_code)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(summary="Delete a QR code", responses={204: None})
    def delete(self, request, short_code):
        qr_code = self.get_qr_code(short_code, request.user)
        if not qr_code:
            return Response(
                {'error': 'QR code not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        qr_code.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RedirectQRView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Redirect to original URL (scan tracking)",
        responses={302: OpenApiResponse(description="Redirects to the original URL")},
    )
    def get(self, request, short_code):
        try:
            qr_code = QRCode.objects.get(short_code=short_code)
        except QRCode.DoesNotExist:
            return Response(
                {'error': 'QR code not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        Scan.objects.create(
            qr_code=qr_code,
            ip_address=ip_address,
            user_agent=user_agent
        )

        parsed = urlparse(qr_code.original_url)
        if parsed.scheme not in ('http', 'https'):
            return Response(
                {'error': 'Invalid redirect URL'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return redirect(qr_code.original_url)


class QRCodeImageView(APIView):
    """Serve QR code images by short_code. Public endpoint."""
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Get QR code image",
        responses={(200, 'image/png'): bytes},
    )
    def get(self, request, short_code):
        if '/' in short_code or '\\' in short_code or '..' in short_code:
            raise Http404

        image_path = os.path.join(settings.MEDIA_ROOT, 'qr_codes', f'{short_code}.png')
        real_path = os.path.realpath(image_path)
        allowed_dir = os.path.realpath(os.path.join(settings.MEDIA_ROOT, 'qr_codes'))
        if not real_path.startswith(allowed_dir + os.sep):
            raise Http404

        if not os.path.exists(real_path):
            raise Http404
        return FileResponse(open(real_path, 'rb'), content_type='image/png')
