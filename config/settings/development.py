from .base import *
import dj_database_url
import environ
from django.core.exceptions import ImproperlyConfigured

env = environ.Env()
environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('DJANGO_SECRET_KEY', default=None)
if not SECRET_KEY:
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY is required. Copy .env.example to .env and fill in a value."
    )

DEBUG = True
ALLOWED_HOSTS = ['*']

# Accept either DATABASE_URL (single connection string) or the discrete
# DB_* variables. Defaults are tuned for a local Postgres install so a
# new contributor can clone, fill in DJANGO_SECRET_KEY, and run the app.
DATABASE_URL = env('DATABASE_URL', default=None)
if DATABASE_URL:
    DATABASES = {'default': dj_database_url.parse(DATABASE_URL)}
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': env('DB_NAME', default='qr_service'),
            'USER': env('DB_USER', default='postgres'),
            'PASSWORD': env('DB_PASSWORD', default=''),
            'HOST': env('DB_HOST', default='localhost'),
            'PORT': env('DB_PORT', default='5432'),
        }
    }
