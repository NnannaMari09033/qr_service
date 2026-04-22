from django.contrib.auth.models import User
from django.core.cache import cache
from django_otp.oath import totp as oath_totp
from django_otp.plugins.otp_totp.models import TOTPDevice
from rest_framework import status
from rest_framework.test import APITestCase


def valid_totp_code(device):
    """Generate the current valid 6-digit TOTP code for a device."""
    return str(oath_totp(device.bin_key)).zfill(6)


class RegisterViewTest(APITestCase):
    def setUp(self):
        cache.clear()

    def test_creates_user_with_matching_passwords(self):
        resp = self.client.post('/auth/register/', {
            'username': 'alice',
            'email': 'a@x.com',
            'password': 'strong-pw-123',
            'password2': 'strong-pw-123',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username='alice').exists())

    def test_rejects_password_mismatch(self):
        resp = self.client.post('/auth/register/', {
            'username': 'alice',
            'email': 'a@x.com',
            'password': 'strong-pw-123',
            'password2': 'different-pw-456',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(username='alice').exists())

    def test_rejects_short_password(self):
        resp = self.client.post('/auth/register/', {
            'username': 'alice',
            'email': 'a@x.com',
            'password': 'short',
            'password2': 'short',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class JWTLoginTest(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username='alice', email='a@x.com', password='strong-pw-123'
        )

    def test_login_returns_access_and_refresh(self):
        resp = self.client.post('/auth/login/', {
            'username': 'alice',
            'password': 'strong-pw-123',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('access', resp.data)
        self.assertIn('refresh', resp.data)

    def test_login_rejects_wrong_password(self):
        resp = self.client.post('/auth/login/', {
            'username': 'alice',
            'password': 'wrong',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class ProfileViewTest(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username='alice', email='a@x.com', password='strong-pw-123'
        )

    def test_requires_authentication(self):
        resp = self.client.get('/auth/me/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_returns_profile_with_has_2fa_false(self):
        self.client.force_authenticate(self.user)
        resp = self.client.get('/auth/me/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['username'], 'alice')
        self.assertEqual(resp.data['email'], 'a@x.com')
        self.assertFalse(resp.data['has_2fa'])

    def test_has_2fa_true_when_confirmed_device_exists(self):
        TOTPDevice.objects.create(user=self.user, name='app', confirmed=True)
        self.client.force_authenticate(self.user)
        resp = self.client.get('/auth/me/')
        self.assertTrue(resp.data['has_2fa'])

    def test_has_2fa_false_when_only_unconfirmed_device_exists(self):
        TOTPDevice.objects.create(user=self.user, name='app', confirmed=False)
        self.client.force_authenticate(self.user)
        resp = self.client.get('/auth/me/')
        self.assertFalse(resp.data['has_2fa'])

    def test_update_profile(self):
        self.client.force_authenticate(self.user)
        resp = self.client.put('/auth/me/', {
            'username': 'alice2',
            'email': 'a2@x.com',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'alice2')
        self.assertEqual(self.user.email, 'a2@x.com')

    def test_delete_account(self):
        self.client.force_authenticate(self.user)
        resp = self.client.delete('/auth/me/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())


class TwoFactorSetupTest(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username='alice', email='a@x.com', password='strong-pw-123'
        )
        self.client.force_authenticate(self.user)

    def test_setup_creates_unconfirmed_device_and_returns_qr(self):
        resp = self.client.post('/auth/2fa/setup/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('qr_code', resp.data)
        self.assertTrue(resp.data['qr_code'].startswith('data:image/png;base64,'))
        self.assertIn('secret', resp.data)
        self.assertEqual(
            TOTPDevice.objects.filter(user=self.user, confirmed=False).count(), 1
        )

    def test_calling_setup_twice_replaces_unconfirmed_device(self):
        self.client.post('/auth/2fa/setup/')
        self.client.post('/auth/2fa/setup/')
        self.assertEqual(
            TOTPDevice.objects.filter(user=self.user, confirmed=False).count(), 1
        )


class TwoFactorConfirmTest(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username='alice', email='a@x.com', password='strong-pw-123'
        )
        self.client.force_authenticate(self.user)
        self.client.post('/auth/2fa/setup/')
        self.device = TOTPDevice.objects.get(user=self.user, confirmed=False)

    def test_confirm_with_valid_code_activates_device(self):
        resp = self.client.post(
            '/auth/2fa/confirm/',
            {'code': valid_totp_code(self.device)},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.device.refresh_from_db()
        self.assertTrue(self.device.confirmed)

    def test_confirm_with_invalid_code_fails(self):
        resp = self.client.post(
            '/auth/2fa/confirm/', {'code': '000000'}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.device.refresh_from_db()
        self.assertFalse(self.device.confirmed)

    def test_confirm_without_prior_setup_fails(self):
        self.device.delete()
        resp = self.client.post(
            '/auth/2fa/confirm/', {'code': '000000'}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class TwoFactorVerifyTest(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username='alice', email='a@x.com', password='strong-pw-123'
        )
        self.client.force_authenticate(self.user)
        self.device = TOTPDevice.objects.create(
            user=self.user, name='app', confirmed=True
        )

    def test_verify_with_valid_code(self):
        resp = self.client.post(
            '/auth/2fa/verify/',
            {'code': valid_totp_code(self.device)},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['verified'])

    def test_verify_with_invalid_code(self):
        resp = self.client.post(
            '/auth/2fa/verify/', {'code': '000000'}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class TwoFactorDisableTest(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username='alice', email='a@x.com', password='strong-pw-123'
        )
        self.client.force_authenticate(self.user)

    def test_disable_with_valid_code_removes_device(self):
        device = TOTPDevice.objects.create(
            user=self.user, name='app', confirmed=True
        )
        resp = self.client.post(
            '/auth/2fa/disable/',
            {'code': valid_totp_code(device)},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(TOTPDevice.objects.filter(user=self.user).exists())

    def test_disable_with_invalid_code_keeps_device(self):
        TOTPDevice.objects.create(user=self.user, name='app', confirmed=True)
        resp = self.client.post(
            '/auth/2fa/disable/', {'code': '000000'}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(
            TOTPDevice.objects.filter(user=self.user, confirmed=True).exists()
        )

    def test_disable_when_2fa_not_enabled_fails(self):
        resp = self.client.post(
            '/auth/2fa/disable/', {'code': '000000'}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
