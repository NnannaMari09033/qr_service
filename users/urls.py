from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    RegisterView, ProfileView,
    Setup2FAView, Confirm2FAView, Disable2FAView, Verify2FAView,
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', TokenObtainPairView.as_view(), name='login'),
    path('refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('me/', ProfileView.as_view(), name='profile'),
    # 2FA
    path('2fa/setup/', Setup2FAView.as_view(), name='2fa-setup'),
    path('2fa/confirm/', Confirm2FAView.as_view(), name='2fa-confirm'),
    path('2fa/disable/', Disable2FAView.as_view(), name='2fa-disable'),
    path('2fa/verify/', Verify2FAView.as_view(), name='2fa-verify'),
]
