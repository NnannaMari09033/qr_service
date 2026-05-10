import io
import uuid
from urllib.parse import urlparse

import qrcode
from django.db import IntegrityError
from qr.models import QRCode

MAX_RETRIES = 5
ALLOWED_SCHEMES = ('http', 'https')


def generate_qr_code(original_url, owner=None):
    """Reserve a unique short_code and create the QRCode row.

    No PNG is written to disk — image bytes are generated on demand by
    QRCodeImageView. This keeps the service stateless so user data never
    "disappears" when the container's filesystem is reset (e.g., on every
    Railway redeploy).
    """
    parsed = urlparse(original_url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise ValueError("Only http and https URLs are allowed")

    for _ in range(MAX_RETRIES):
        short_code = uuid.uuid4().hex[:8]
        try:
            return QRCode.objects.create(
                original_url=original_url,
                short_code=short_code,
                owner=owner,
            )
        except IntegrityError:
            continue

    raise RuntimeError("Failed to generate a unique short code after multiple attempts")


def render_qr_png(redirect_url):
    """Return PNG bytes for a QR encoding the given redirect URL."""
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(redirect_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return buffer.getvalue()
