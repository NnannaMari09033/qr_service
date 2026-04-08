from django.db import models
from qr.models import QRCode

class Scan(models.Model):
    qr_code = models.ForeignKey(QRCode, on_delete=models.CASCADE, related_name='scans')
    scanned_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = 'scans'
        ordering = ['-scanned_at']

    def __str__(self):
        return f"{self.qr_code.short_code} scanned at {self.scanned_at}"