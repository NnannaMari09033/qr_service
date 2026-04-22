import tempfile

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from analytics.models import Scan
from qr.services.qr_service import generate_qr_code

TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix='analytics_test_media_')


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class QRCodeStatsViewTest(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username='alice', email='a@x.com', password='strong-pw-123'
        )
        self.other = User.objects.create_user(
            username='bob', email='b@x.com', password='strong-pw-123'
        )
        self.qr = generate_qr_code('https://example.com', owner=self.user)

    def test_requires_authentication(self):
        resp = self.client.get(f'/analytics/{self.qr.short_code}/stats/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_returns_total_scans_for_own_code(self):
        Scan.objects.create(qr_code=self.qr, ip_address='1.2.3.4')
        Scan.objects.create(qr_code=self.qr, ip_address='5.6.7.8')

        self.client.force_authenticate(self.user)
        resp = self.client.get(f'/analytics/{self.qr.short_code}/stats/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['total_scans'], 2)
        self.assertEqual(resp.data['short_code'], self.qr.short_code)
        self.assertEqual(resp.data['original_url'], 'https://example.com')

    def test_other_user_cannot_access_stats(self):
        self.client.force_authenticate(self.other)
        resp = self.client.get(f'/analytics/{self.qr.short_code}/stats/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_404_for_missing_code(self):
        self.client.force_authenticate(self.user)
        resp = self.client.get('/analytics/nosuchcode/stats/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_stats_includes_empty_aggregates_when_no_scans(self):
        self.client.force_authenticate(self.user)
        resp = self.client.get(f'/analytics/{self.qr.short_code}/stats/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['total_scans'], 0)
