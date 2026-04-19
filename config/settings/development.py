from .base import *
import environ
from django.core.exceptions import ImproperlyConfigured

env = environ.Env()
environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY environment variable is required")

DEBUG = True
ALLOWED_HOSTS = ['*']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST'),
        'PORT': env('DB_PORT'),
    }
}
