from django.contrib.auth.models import User
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase

from analytics.models import Scan
from qr.models import QRCode
from qr.services.qr_service import generate_qr_code


class QRCodeServiceTest(APITestCase):
    def test_rejects_non_http_schemes(self):
        bad_urls = [
            'javascript:alert(1)',
            'ftp://example.com/file',
            'file:///etc/passwd',
            'data:text/html,<script>alert(1)</script>',
        ]
        for url in bad_urls:
            with self.assertRaises(ValueError, msg=f'should reject {url}'):
                generate_qr_code(url)

    def test_accepts_http_and_https(self):
        qr_http = generate_qr_code('http://example.com')
        qr_https = generate_qr_code('https://example.com')
        self.assertEqual(qr_http.original_url, 'http://example.com')
        self.assertEqual(qr_https.original_url, 'https://example.com')
        self.assertEqual(len(qr_http.short_code), 8)


class QRCodeListViewTest(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username='alice', email='a@x.com', password='strong-pw-123')
        self.other = User.objects.create_user(username='bob', email='b@x.com', password='strong-pw-123')

    def test_create_requires_original_url(self):
        self.client.force_authenticate(self.user)
        resp = self.client.post('/qr/', {}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_rejects_non_http_scheme(self):
        self.client.force_authenticate(self.user)
        resp = self.client.post('/qr/', {'original_url': 'javascript:alert(1)'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_succeeds_for_authenticated_user(self):
        self.client.force_authenticate(self.user)
        resp = self.client.post('/qr/', {'original_url': 'https://example.com'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(QRCode.objects.filter(owner=self.user).count(), 1)

    def test_list_only_returns_users_own_codes(self):
        generate_qr_code('https://alice.com', owner=self.user)
        generate_qr_code('https://bob.com', owner=self.other)

        self.client.force_authenticate(self.user)
        resp = self.client.get('/qr/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]['original_url'], 'https://alice.com')

    def test_list_empty_for_anonymous(self):
        generate_qr_code('https://alice.com', owner=self.user)
        resp = self.client.get('/qr/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 0)

    def test_anonymous_create_throttled_after_burst(self):
        # Configured rate for anon_create_qr is 5/hour.
        last = None
        for _ in range(6):
            last = self.client.post(
                '/qr/', {'original_url': 'https://example.com'}, format='json'
            )
        self.assertEqual(last.status_code, status.HTTP_429_TOO_MANY_REQUESTS)


class QRCodeDetailViewTest(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username='alice', email='a@x.com', password='strong-pw-123')
        self.other = User.objects.create_user(username='bob', email='b@x.com', password='strong-pw-123')
        self.qr = generate_qr_code('https://example.com', owner=self.user)

    def test_requires_authentication(self):
        resp = self.client.get(f'/qr/{self.qr.short_code}/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_owner_can_retrieve(self):
        self.client.force_authenticate(self.user)
        resp = self.client.get(f'/qr/{self.qr.short_code}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['short_code'], self.qr.short_code)

    def test_other_user_gets_404(self):
        self.client.force_authenticate(self.other)
        resp = self.client.get(f'/qr/{self.qr.short_code}/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_owner_can_update_url(self):
        self.client.force_authenticate(self.user)
        resp = self.client.put(
            f'/qr/{self.qr.short_code}/',
            {'original_url': 'https://updated.com'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.qr.refresh_from_db()
        self.assertEqual(self.qr.original_url, 'https://updated.com')

    def test_update_rejects_bad_scheme(self):
        self.client.force_authenticate(self.user)
        resp = self.client.put(
            f'/qr/{self.qr.short_code}/',
            {'original_url': 'javascript:alert(1)'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_owner_can_delete(self):
        self.client.force_authenticate(self.user)
        resp = self.client.delete(f'/qr/{self.qr.short_code}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(QRCode.objects.filter(pk=self.qr.pk).exists())

    def test_other_user_cannot_delete(self):
        self.client.force_authenticate(self.other)
        resp = self.client.delete(f'/qr/{self.qr.short_code}/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(QRCode.objects.filter(pk=self.qr.pk).exists())


class RedirectQRViewTest(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username='alice', email='a@x.com', password='strong-pw-123')
        self.other = User.objects.create_user(username='bob', email='b@x.com', password='strong-pw-123')
        self.qr = generate_qr_code('https://example.com', owner=self.user)

    def test_anon_sees_interstitial_and_no_scan_recorded(self):
        resp = self.client.get(f'/qr/redirect/{self.qr.short_code}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn(b'leaving QR Service', resp.content)
        self.assertEqual(Scan.objects.filter(qr_code=self.qr).count(), 0)

    def test_anon_with_go_param_redirects_and_records_scan(self):
        resp = self.client.get(f'/qr/redirect/{self.qr.short_code}/?go=1')
        self.assertEqual(resp.status_code, status.HTTP_302_FOUND)
        self.assertEqual(resp['Location'], 'https://example.com')
        self.assertEqual(Scan.objects.filter(qr_code=self.qr).count(), 1)

    def test_owner_redirects_directly(self):
        self.client.force_authenticate(self.user)
        resp = self.client.get(f'/qr/redirect/{self.qr.short_code}/')
        self.assertEqual(resp.status_code, status.HTTP_302_FOUND)
        self.assertEqual(resp['Location'], 'https://example.com')
        self.assertEqual(Scan.objects.filter(qr_code=self.qr).count(), 1)

    def test_non_owner_authenticated_sees_interstitial(self):
        self.client.force_authenticate(self.other)
        resp = self.client.get(f'/qr/redirect/{self.qr.short_code}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn(b'leaving QR Service', resp.content)

    def test_404_for_missing_code(self):
        resp = self.client.get('/qr/redirect/doesnotexist/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


class QRCodeImageViewTest(APITestCase):
    """The image endpoint generates PNGs on demand from the DB row.

    Nothing is stored on disk, so the test asserts the PNG can be served
    even after the entire MEDIA_ROOT is wiped — which is exactly what
    happens on a Railway redeploy.
    """

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username='alice', email='a@x.com', password='strong-pw-123')
        self.qr = generate_qr_code('https://example.com', owner=self.user)

    def test_serves_png(self):
        resp = self.client.get(f'/qr/image/{self.qr.short_code}.png')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp['Content-Type'], 'image/png')
        # PNG magic bytes — proves we returned a real image, not an empty body.
        self.assertEqual(resp.content[:8], b'\x89PNG\r\n\x1a\n')

    def test_404_for_unknown_short_code(self):
        resp = self.client.get('/qr/image/nosuchcode.png')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_response_is_cacheable(self):
        # The QR encodes /qr/redirect/<short_code>/ which is keyed only on
        # short_code, so the PNG never changes — safe to cache long-term.
        resp = self.client.get(f'/qr/image/{self.qr.short_code}.png')
        self.assertIn('immutable', resp['Cache-Control'])

    def test_image_survives_disk_wipe(self):
        # Regression test for the "QR codes vanish after restart" bug:
        # PNG generation must depend only on the DB row, not on any file
        # we previously wrote out.
        import tempfile
        from django.conf import settings

        with tempfile.TemporaryDirectory() as empty_root:
            # Simulate Railway nuking the container disk by pointing
            # MEDIA_ROOT at a fresh empty dir. Old, unrelated files are
            # also irrelevant — the on-demand renderer reads neither.
            original = settings.MEDIA_ROOT
            settings.MEDIA_ROOT = empty_root
            try:
                resp = self.client.get(f'/qr/image/{self.qr.short_code}.png')
                self.assertEqual(resp.status_code, status.HTTP_200_OK)
                self.assertEqual(resp['Content-Type'], 'image/png')
            finally:
                settings.MEDIA_ROOT = original
