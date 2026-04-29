from .base import *
import os
from django.core.exceptions import ImproperlyConfigured

if not SECRET_KEY:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY environment variable is required")

DEBUG = False
_raw_allowed_hosts = os.environ.get('DJANGO_ALLOWED_HOSTS', '')
ALLOWED_HOSTS = [h.strip() for h in _raw_allowed_hosts.split(',') if h.strip()]

import sys
print(f"[settings] DJANGO_SETTINGS_MODULE = {os.environ.get('DJANGO_SETTINGS_MODULE', '<not set>')}", file=sys.stderr, flush=True)
print(f"[settings] DJANGO_ALLOWED_HOSTS raw env = {_raw_allowed_hosts!r}", file=sys.stderr, flush=True)
print(f"[settings] ALLOWED_HOSTS parsed = {ALLOWED_HOSTS!r}", file=sys.stderr, flush=True)

MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': True,
        },
    },
}