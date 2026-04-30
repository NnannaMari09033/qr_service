import tempfile

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase

from analytics.models import Scan
from qr.models import QRCode
from qr.services.qr_service import generate_qr_code
from qr.views import QRCodeImageView

TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix='qr_test_media_')


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
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


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
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


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
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


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
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


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class QRCodeImageViewTest(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username='alice', email='a@x.com', password='strong-pw-123')
        self.qr = generate_qr_code('https://example.com', owner=self.user)

    def test_serves_png(self):
        resp = self.client.get(f'/qr/image/{self.qr.short_code}.png')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp['Content-Type'], 'image/png')

    def test_404_for_missing_image(self):
        resp = self.client.get('/qr/image/nosuchcode.png')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_blocks_path_traversal(self):
        view = QRCodeImageView.as_view()
        factory = APIRequestFactory()
        for bad in ['..', '../secret', 'foo/bar', 'foo\\bar']:
            req = factory.get('/')
            resp = view(req, short_code=bad)
            self.assertEqual(resp.status_code, 404, msg=f'should reject {bad}')
