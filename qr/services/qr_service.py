import os
import uuid
from urllib.parse import urlparse

import qrcode
from django.conf import settings
from django.db import IntegrityError
from qr.models import QRCode

MAX_RETRIES = 5
ALLOWED_SCHEMES = ('http', 'https')


def generate_qr_code(original_url, owner=None):
    parsed = urlparse(original_url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise ValueError("Only http and https URLs are allowed")
    for _ in range(MAX_RETRIES):
        short_code = str(uuid.uuid4()).replace('-', '')[:8]

        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        redirect_url = f"/qr/redirect/{short_code}/"
        qr.add_data(redirect_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        image_dir = os.path.join(settings.MEDIA_ROOT, 'qr_codes')
        os.makedirs(image_dir, exist_ok=True)
        image_path = os.path.join(image_dir, f"{short_code}.png")
        img.save(image_path)

        try:
            qr_code = QRCode.objects.create(
                original_url=original_url,
                short_code=short_code,
                image_path=image_path,
                owner=owner,
            )
            return qr_code
        except IntegrityError:
            os.remove(image_path)
            continue

    raise RuntimeError("Failed to generate a unique short code after multiple attempts")