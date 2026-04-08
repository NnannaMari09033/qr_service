from django.db import models
import uuid

class QRCode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    original_url = models.URLField()
    short_code = models.CharField(max_length=20, unique=True)
    image_path = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'qr_codes'
        ordering = ['-created_at']

    def __str__(self):
        return self.short_code