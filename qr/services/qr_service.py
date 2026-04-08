import os
import uuid
import qrcode
from django.conf import settings
from django.db import IntegrityError
from qr.models import QRCode

def generate_qr_code(original_url):
    try:
        short_code = str(uuid.uuid4()).replace('-', '')[:8]

        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(f"http://yourdomain.com/qr/{short_code}")
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        image_path = os.path.join(settings.MEDIA_ROOT, 'qr_codes', f"{short_code}.png")
        img.save(image_path)

        qr_code = QRCode.objects.create(
            original_url=original_url,
            short_code=short_code,
            image_path=image_path
        )
        return qr_code
    except IntegrityError:
        return generate_qr_code(original_url)