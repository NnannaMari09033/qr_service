from .base import *
import os
from django.core.exceptions import ImproperlyConfigured

if not SECRET_KEY:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY environment variable is required")

DEBUG = False

# Hosts come from DJANGO_ALLOWED_HOSTS (comma-separated). The ".up.railway.app"
# subdomain wildcard is included by default because the Railway platform always
# assigns a subdomain there, and forgetting to add it is the most common cause
# of a "DisallowedHost" error on a first Railway deploy.
_DEFAULT_HOSTS = ['.up.railway.app', 'localhost', '127.0.0.1']
_env_hosts = [h.strip() for h in os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',') if h.strip()]
ALLOWED_HOSTS = list({*_DEFAULT_HOSTS, *_env_hosts})


def _csrf_origin(host):
    # Django expects an explicit scheme. A leading "." in ALLOWED_HOSTS is the
    # subdomain wildcard syntax for that setting; CSRF_TRUSTED_ORIGINS uses
    # "https://*.example.com" instead.
    if host.startswith('.'):
        return f'https://*{host}'
    return f'https://{host}'


CSRF_TRUSTED_ORIGINS = [
    _csrf_origin(h) for h in ALLOWED_HOSTS if h not in ('localhost', '127.0.0.1')
]

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