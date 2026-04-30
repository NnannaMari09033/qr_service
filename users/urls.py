from django.urls import path

from .views import (
    Confirm2FAView,
    CookieRefreshView,
    Disable2FAView,
    LoginView,
    LogoutView,
    ProfileView,
    RegisterView,
    Setup2FAView,
    Verify2FAView,
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('refresh/', CookieRefreshView.as_view(), name='token-refresh'),
    path('me/', ProfileView.as_view(), name='profile'),
    path('2fa/setup/', Setup2FAView.as_view(), name='2fa-setup'),
    path('2fa/confirm/', Confirm2FAView.as_view(), name='2fa-confirm'),
    path('2fa/disable/', Disable2FAView.as_view(), name='2fa-disable'),
    path('2fa/verify/', Verify2FAView.as_view(), name='2fa-verify'),
]
