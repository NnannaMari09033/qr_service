import json
from urllib.parse import urlparse

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.shortcuts import redirect, render
from django.http import HttpResponse
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .models import QRCode
from .serializers import QRCodeSerializer
from .services.qr_service import generate_qr_code, render_qr_png
from .throttles import AnonCreateQRThrottle
from analytics.models import Scan


class CreateQRInputSerializer(serializers.Serializer):
    """Tells Swagger what the POST /qr/ body looks like."""
    original_url = serializers.URLField()


class QRCodeListView(APIView):
    permission_classes = [AllowAny]

    def get_throttles(self):
        # Apply a stricter throttle to anonymous POSTs so the public
        # create endpoint cannot be used to flood the short-code namespace
        # or chew up disk. Authenticated users keep the default UserRateThrottle.
        if self.request.method == 'POST' and not self.request.user.is_authenticated:
            return [AnonCreateQRThrottle()]
        return super().get_throttles()

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
        qr_code = generate_qr_code(original_url, owner=owner)
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
    """Public redirect endpoint with open-redirect mitigation.

    For owners (authenticated as the QR's creator) and for confirmed
    follow-throughs (?go=1), record the scan and 302 to the destination.
    For everyone else, render an interstitial that displays the destination
    URL so the user can decide whether to continue. This prevents the
    service from being used as a transparent open-redirect for phishing.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Redirect to original URL (scan tracking)",
        responses={
            200: OpenApiResponse(description="Renders an interstitial confirmation page"),
            302: OpenApiResponse(description="Redirects to the original URL"),
        },
    )
    def get(self, request, short_code):
        try:
            qr_code = QRCode.objects.get(short_code=short_code)
        except QRCode.DoesNotExist:
            return Response(
                {'error': 'QR code not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        parsed = urlparse(qr_code.original_url)
        if parsed.scheme not in ('http', 'https'):
            return Response(
                {'error': 'Invalid redirect URL'},
                status=status.HTTP_400_BAD_REQUEST
            )

        is_owner = (
            request.user.is_authenticated and qr_code.owner_id == request.user.id
        )
        confirmed = request.GET.get('go') == '1'

        if not (is_owner or confirmed):
            continue_url = f"{request.path}?go=1"
            return render(request, 'redirect_interstitial.html', {
                'destination_json': json.dumps(qr_code.original_url),
                'continue_url_json': json.dumps(continue_url),
            })

        Scan.objects.create(
            qr_code=qr_code,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
        )
        return redirect(qr_code.original_url)


class QRCodeImageView(APIView):
    """Serve a QR PNG by short_code. Public endpoint.

    The PNG is generated on demand from the QRCode row — nothing is stored
    on disk. This makes the service stateless: an ephemeral filesystem
    (e.g. on Railway redeploys) cannot lose anyone's data, because the only
    durable artifact is the database row.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Get QR code image",
        responses={(200, 'image/png'): bytes},
    )
    def get(self, request, short_code):
        try:
            qr_code = QRCode.objects.get(short_code=short_code)
        except QRCode.DoesNotExist:
            return Response(
                {'error': 'QR code not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        redirect_url = request.build_absolute_uri(f'/qr/redirect/{qr_code.short_code}/')
        png_bytes = render_qr_png(redirect_url)

        response = HttpResponse(png_bytes, content_type='image/png')
        # The QR encodes the redirect URL, which is keyed only on short_code
        # and never changes — even when the destination URL is updated. Safe
        # to cache aggressively.
        response['Cache-Control'] = 'public, max-age=31536000, immutable'
        return response
