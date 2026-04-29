"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os
import sys

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

print(f"[wsgi] DJANGO_SETTINGS_MODULE = {os.environ.get('DJANGO_SETTINGS_MODULE', '<not set>')}", file=sys.stderr, flush=True)
print(f"[wsgi] DJANGO_ALLOWED_HOSTS env = {os.environ.get('DJANGO_ALLOWED_HOSTS', '<not set>')!r}", file=sys.stderr, flush=True)
print(f"[wsgi] DJANGO_DEBUG env = {os.environ.get('DJANGO_DEBUG', '<not set>')!r}", file=sys.stderr, flush=True)
print(f"[wsgi] DJANGO_SECRET_KEY set? {bool(os.environ.get('DJANGO_SECRET_KEY'))}", file=sys.stderr, flush=True)

application = get_wsgi_application()

from django.conf import settings as _s
print(f"[wsgi] settings.ALLOWED_HOSTS = {_s.ALLOWED_HOSTS!r}", file=sys.stderr, flush=True)
print(f"[wsgi] settings.DEBUG = {_s.DEBUG!r}", file=sys.stderr, flush=True)
