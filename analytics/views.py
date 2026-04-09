from django.db.models import Count
from django.db.models.functions import TruncDate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from qr.models import QRCode
from .models import Scan


class QRCodeStatsView(APIView):
    def get(self, request, short_code):
        try:
            qr_code = QRCode.objects.get(short_code=short_code)
        except QRCode.DoesNotExist:
            return Response(
                {'error': 'QR code not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        scans = Scan.objects.filter(qr_code=qr_code)
        total_scans = scans.count()

        scans_by_country = dict(
            scans.values_list('country').annotate(count=Count('id'))
        )

        scans_by_date = {
            str(item['date']): item['count']
            for item in scans.annotate(date=TruncDate('scanned_at')).values('date').annotate(count=Count('id'))
        }

        return Response({
            'short_code': short_code,
            'original_url': qr_code.original_url,
            'total_scans': total_scans,
            'scans_by_country': scans_by_country,
            'scans_by_date': scans_by_date,
        }, status=status.HTTP_200_OK)
    