from django.urls import path
from .views import QRCodeStatsView

urlpatterns = [
    path('<str:short_code>/stats/', QRCodeStatsView.as_view(), name='qr-stats'),
]
