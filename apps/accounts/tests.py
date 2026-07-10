from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import translation

User = get_user_model()


class AuthFlowTests(TestCase):
    def setUp(self):
        # django-ratelimit counters live in the process cache; reset between tests.
        cache.clear()
        # Translation state is process-global and leaks across tests; reset to en.
        translation.activate("en")

    def test_signup_creates_user_and_logs_in(self):
        resp = self.client.post(
            reverse("accounts:signup"),
            {
                "email": "buyer@test.com",
                "first_name": "Bee",
                "last_name": "Yer",
                "password1": "Str0ngPass!23",
                "password2": "Str0ngPass!23",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(User.objects.filter(email="buyer@test.com").exists())
        self.assertIn("_auth_user_id", self.client.session)

    def test_duplicate_email_rejected(self):
        User.objects.create_user(email="dupe@test.com", password="Str0ngPass!23")
        resp = self.client.post(
            reverse("accounts:signup"),
            {
                "email": "dupe@test.com",
                "first_name": "A",
                "last_name": "B",
                "password1": "Str0ngPass!23",
                "password2": "Str0ngPass!23",
            },
        )
        self.assertEqual(resp.status_code, 200)  # re-rendered with error
        self.assertContains(resp, "already exists")

    def test_login_by_email_and_logout(self):
        User.objects.create_user(email="buyer@test.com", password="Str0ngPass!23")
        resp = self.client.post(
            reverse("accounts:login"),
            {"username": "buyer@test.com", "password": "Str0ngPass!23"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("_auth_user_id", self.client.session)
        # logout is POST-only
        self.assertEqual(self.client.get(reverse("accounts:logout")).status_code, 405)
        self.client.post(reverse("accounts:logout"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_respects_safe_next(self):
        User.objects.create_user(email="buyer@test.com", password="Str0ngPass!23")
        resp = self.client.post(
            reverse("accounts:login"),
            {"username": "buyer@test.com", "password": "Str0ngPass!23", "next": "/orders/mine/"},
        )
        self.assertRedirects(resp, "/orders/mine/", fetch_redirect_response=False)

    def test_login_rejects_open_redirect(self):
        User.objects.create_user(email="buyer@test.com", password="Str0ngPass!23")
        home = reverse("catalog:home")
        for evil in ["https://evil.example/", "//evil.example", "/\\evil.example", "\\/evil.example"]:
            resp = self.client.post(
                reverse("accounts:login"),
                {"username": "buyer@test.com", "password": "Str0ngPass!23", "next": evil},
            )
            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp["Location"], home, f"open redirect not blocked: {evil!r}")

    def test_password_reset_sends_console_email(self):
        User.objects.create_user(email="buyer@test.com", password="Str0ngPass!23")
        with override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            resp = self.client.post(reverse("accounts:password_reset"), {"email": "buyer@test.com"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("reset", mail.outbox[0].subject.lower())

    def test_auth_pages_load_in_both_languages(self):
        for prefix in ["", "/ar"]:
            for path in ["/accounts/login/", "/accounts/signup/", "/accounts/password-reset/"]:
                self.assertEqual(self.client.get(prefix + path).status_code, 200, prefix + path)
