from .models import QRCode
from rest_framework import serializers

class QRCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = QRCode
        fields = ['id', 'original_url', 'short_code', 'created_at']