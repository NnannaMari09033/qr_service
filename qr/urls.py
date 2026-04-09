from django.urls import path
from .views import QRCodeListView, QRCodeDetailView, RedirectQRView

urlpatterns = [
    path('', QRCodeListView.as_view(), name='qr-list'),
    path('redirect/<str:short_code>/', RedirectQRView.as_view(), name='qr-redirect'),
    path('<str:short_code>/', QRCodeDetailView.as_view(), name='qr-detail'),
]


