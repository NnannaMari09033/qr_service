from rest_framework.throttling import AnonRateThrottle


class AnonCreateQRThrottle(AnonRateThrottle):
    """Stricter throttle for anonymous QR creation.

    The default AnonRateThrottle (30/min) is generous for read traffic but
    lets a single IP create 1,800 QR codes per hour, which is enough to
    fill the codebook namespace and exhaust disk for short-code storage.
    Cap unauthenticated POST /qr/ at a much lower rate.
    """
    scope = 'anon_create_qr'
