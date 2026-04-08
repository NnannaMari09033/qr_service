from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import redirect
from .models import QRCode
from .serializers import QRCodeSerializer
from .services.qr_service import generate_qr_code
from analytics.models import Scan


class QRCodeListView(APIView):
    def get(self, request):
        qr_codes = QRCode.objects.all()
        serializer = QRCodeSerializer(qr_codes, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        original_url = request.data.get('original_url')

        if not original_url:
            return Response(
                {'error': 'original_url is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        qr_code = generate_qr_code(original_url)
        serializer = QRCodeSerializer(qr_code)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class QRCodeDetailView(APIView):
    def get(self, request, short_code):
        try:
            qr_code = QRCode.objects.get(short_code=short_code)
        except QRCode.DoesNotExist:
            return Response(
                {'error': 'QR code not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = QRCodeSerializer(qr_code)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, short_code):
        try:
            qr_code = QRCode.objects.get(short_code=short_code)
        except QRCode.DoesNotExist:
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

        qr_code.original_url = original_url
        qr_code.save()
        serializer = QRCodeSerializer(qr_code)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, short_code):
        try:
            qr_code = QRCode.objects.get(short_code=short_code)
        except QRCode.DoesNotExist:
            return Response(
                {'error': 'QR code not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        qr_code.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RedirectQRView(APIView):
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

        return redirect(qr_code.original_url)