from django.urls import path
from .views import QRCodeListView, QRCodeDetailView, RedirectQRView, QRCodeImageView

urlpatterns = [
    path('', QRCodeListView.as_view(), name='qr-list'),
    path('redirect/<str:short_code>/', RedirectQRView.as_view(), name='qr-redirect'),
    path('image/<str:short_code>.png', QRCodeImageView.as_view(), name='qr-image'),
    path('<str:short_code>/', QRCodeDetailView.as_view(), name='qr-detail'),
]


