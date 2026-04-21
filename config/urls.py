from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from .frontend_views import landing_view, login_view, register_view, dashboard_view, settings_view

urlpatterns = [
    # Frontend pages (serve HTML)
    path('', landing_view, name='landing'),
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('settings/', settings_view, name='settings'),

    # Swagger API documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # API endpoints (return JSON)
    path('admin/', admin.site.urls),
    path('qr/', include('qr.urls')),
    path('analytics/', include('analytics.urls')),
    path('auth/', include('users.urls')),

    # Allauth (Google OAuth + email verification)
    path('accounts/', include('allauth.urls')),
]

# Serve media files (QR code images) in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
