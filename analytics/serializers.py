from rest_framework import serializers
from .models import Scan
from qr.serializers import QRCodeSerializer

class ScanSerializer(serializers.ModelSerializer):
    qr_code = QRCodeSerializer(read_only=True)

    class Meta:
        model = Scan
        fields = ['id', 'qr_code', 'scanned_at', 'ip_address', 'user_agent', 'country']