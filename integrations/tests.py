from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse


class MegaverseBridgeHealthTests(SimpleTestCase):
    """Security and routing tests for the MajicMall Megaverse bridge."""

    @override_settings(
        ALLOWED_HOSTS=["testserver"],
        MEGAVERSE_BRIDGE_API_KEY="",
    )
    def test_health_fails_closed_when_bridge_is_not_configured(self):
        response = self.client.get(
            reverse("integrations:bridge-health"),
            secure=True,
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"], "bridge_not_configured")

    @override_settings(
        ALLOWED_HOSTS=["testserver"],
        MEGAVERSE_BRIDGE_API_KEY="test-bridge-secret",
    )
    def test_health_rejects_missing_authorization_header(self):
        response = self.client.get(
            reverse("integrations:bridge-health"),
            secure=True,
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"], "unauthorized")

    @override_settings(
        ALLOWED_HOSTS=["testserver"],
        MEGAVERSE_BRIDGE_API_KEY="test-bridge-secret",
    )
    def test_health_rejects_malformed_authorization_header(self):
        response = self.client.get(
            reverse("integrations:bridge-health"),
            secure=True,
            HTTP_AUTHORIZATION="Basic test-bridge-secret",
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"], "unauthorized")

    @override_settings(
        ALLOWED_HOSTS=["testserver"],
        MEGAVERSE_BRIDGE_API_KEY="test-bridge-secret",
    )
    def test_health_rejects_invalid_bearer_credential(self):
        response = self.client.get(
            reverse("integrations:bridge-health"),
            secure=True,
            HTTP_AUTHORIZATION="Bearer wrong-secret",
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"], "unauthorized")

    @override_settings(
        ALLOWED_HOSTS=["testserver"],
        MEGAVERSE_BRIDGE_API_KEY="test-bridge-secret",
    )
    def test_health_accepts_valid_bearer_credential(self):
        response = self.client.get(
            reverse("integrations:bridge-health"),
            secure=True,
            HTTP_AUTHORIZATION="Bearer test-bridge-secret",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "ok": True,
                "service": "MajicMall Megaverse",
                "bridge": "integration",
                "version": 1,
            },
        )

    @override_settings(
        ALLOWED_HOSTS=["testserver"],
        MEGAVERSE_BRIDGE_API_KEY="test-bridge-secret",
    )
    def test_health_allows_get_only(self):
        response = self.client.post(
            reverse("integrations:bridge-health"),
            secure=True,
            HTTP_AUTHORIZATION="Bearer test-bridge-secret",
        )

        self.assertEqual(response.status_code, 405)


class MegaverseIdentityTests(TestCase):
    def test_identity_has_stable_public_uuid(self):
        from django.contrib.auth import get_user_model
        from integrations.models import MegaverseIdentity

        User = get_user_model()

        user = User.objects.create_user(
            username="megaverse_identity_test",
            email="megaverse-identity@example.com",
            password=None,
        )

        identity_1, created_1 = MegaverseIdentity.objects.get_or_create(user=user)
        identity_2, created_2 = MegaverseIdentity.objects.get_or_create(user=user)

        self.assertTrue(created_1)
        self.assertFalse(created_2)
        self.assertEqual(identity_1.pk, identity_2.pk)
        self.assertEqual(identity_1.public_id, identity_2.public_id)
        self.assertTrue(identity_1.is_active)

    def test_user_can_have_only_one_megaverse_identity(self):
        from django.contrib.auth import get_user_model
        from django.db import IntegrityError
        from integrations.models import MegaverseIdentity

        User = get_user_model()

        user = User.objects.create_user(
            username="megaverse_identity_unique_test",
            email="megaverse-identity-unique@example.com",
            password=None,
        )

        MegaverseIdentity.objects.create(user=user)

        with self.assertRaises(IntegrityError):
            MegaverseIdentity.objects.create(user=user)


class MegaverseAuthorizationCodeTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        from integrations.models import MegaverseIdentity

        User = get_user_model()

        self.user = User.objects.create_user(
            username="megaverse_authorization_test",
            email="megaverse-authorization@example.com",
            password=None,
        )

        self.identity = MegaverseIdentity.objects.create(user=self.user)

    def test_issue_stores_digest_not_plaintext_code(self):
        from integrations.models import MegaverseAuthorizationCode

        authorization, code = MegaverseAuthorizationCode.issue(
            identity=self.identity,
            destination="atls_hottest",
        )

        authorization.refresh_from_db()

        self.assertEqual(len(code), 43)
        self.assertEqual(len(authorization.code_digest), 64)
        self.assertNotEqual(authorization.code_digest, code)
        self.assertEqual(
            authorization.code_digest,
            MegaverseAuthorizationCode.digest_code(code),
        )
        self.assertEqual(authorization.destination, "atls_hottest")
        self.assertTrue(authorization.is_valid)
        self.assertFalse(authorization.is_used)
        self.assertFalse(authorization.is_expired)

    def test_valid_code_redeems_once(self):
        from integrations.models import MegaverseAuthorizationCode

        authorization, code = MegaverseAuthorizationCode.issue(
            identity=self.identity,
            destination="atls_hottest",
        )

        redeemed_identity = MegaverseAuthorizationCode.redeem(
            code=code,
            destination="atls_hottest",
        )

        authorization.refresh_from_db()

        self.assertEqual(redeemed_identity, self.identity)
        self.assertIsNotNone(authorization.used_at)
        self.assertTrue(authorization.is_used)
        self.assertFalse(authorization.is_valid)

        replay = MegaverseAuthorizationCode.redeem(
            code=code,
            destination="atls_hottest",
        )

        self.assertIsNone(replay)

    def test_wrong_destination_is_rejected_without_consuming_code(self):
        from integrations.models import MegaverseAuthorizationCode

        authorization, code = MegaverseAuthorizationCode.issue(
            identity=self.identity,
            destination="atls_hottest",
        )

        redeemed_identity = MegaverseAuthorizationCode.redeem(
            code=code,
            destination="another_destination",
        )

        authorization.refresh_from_db()

        self.assertIsNone(redeemed_identity)
        self.assertIsNone(authorization.used_at)
        self.assertTrue(authorization.is_valid)

    def test_expired_code_is_rejected_without_consuming_code(self):
        from integrations.models import MegaverseAuthorizationCode

        authorization, code = MegaverseAuthorizationCode.issue(
            identity=self.identity,
            destination="atls_hottest",
            lifetime_seconds=-1,
        )

        redeemed_identity = MegaverseAuthorizationCode.redeem(
            code=code,
            destination="atls_hottest",
        )

        authorization.refresh_from_db()

        self.assertIsNone(redeemed_identity)
        self.assertIsNone(authorization.used_at)
        self.assertTrue(authorization.is_expired)
        self.assertFalse(authorization.is_valid)

    def test_inactive_identity_is_rejected_without_consuming_code(self):
        from integrations.models import MegaverseAuthorizationCode

        self.identity.is_active = False
        self.identity.save(update_fields=["is_active"])

        authorization, code = MegaverseAuthorizationCode.issue(
            identity=self.identity,
            destination="atls_hottest",
        )

        redeemed_identity = MegaverseAuthorizationCode.redeem(
            code=code,
            destination="atls_hottest",
        )

        authorization.refresh_from_db()

        self.assertIsNone(redeemed_identity)
        self.assertIsNone(authorization.used_at)


class MegaverseIdentityExchangeEndpointTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        from integrations.models import MegaverseIdentity

        User = get_user_model()

        self.user = User.objects.create_user(
            username="megaverse_exchange_endpoint_test",
            email="megaverse-exchange-endpoint@example.com",
            password=None,
        )
        self.identity = MegaverseIdentity.objects.create(user=self.user)
        self.url = reverse("integrations:identity-exchange")
        self.authorization = "Bearer test-bridge-secret"

    @override_settings(
        ALLOWED_HOSTS=["testserver"],
        MEGAVERSE_BRIDGE_API_KEY="test-bridge-secret",
    )
    def test_exchange_requires_bridge_authentication(self):
        response = self.client.post(
            self.url,
            data="{}",
            content_type="application/json",
            secure=True,
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"], "unauthorized")

    @override_settings(
        ALLOWED_HOSTS=["testserver"],
        MEGAVERSE_BRIDGE_API_KEY="test-bridge-secret",
    )
    def test_exchange_rejects_malformed_json(self):
        response = self.client.post(
            self.url,
            data="{not-valid-json",
            content_type="application/json",
            secure=True,
            HTTP_AUTHORIZATION=self.authorization,
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "invalid_request")

    @override_settings(
        ALLOWED_HOSTS=["testserver"],
        MEGAVERSE_BRIDGE_API_KEY="test-bridge-secret",
    )
    def test_exchange_requires_authorization_code(self):
        response = self.client.post(
            self.url,
            data="{}",
            content_type="application/json",
            secure=True,
            HTTP_AUTHORIZATION=self.authorization,
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "invalid_request")

    @override_settings(
        ALLOWED_HOSTS=["testserver"],
        MEGAVERSE_BRIDGE_API_KEY="test-bridge-secret",
    )
    def test_exchange_returns_only_stable_public_identity_reference(self):
        import json

        from integrations.models import MegaverseAuthorizationCode

        authorization, code = MegaverseAuthorizationCode.issue(
            identity=self.identity,
            destination="atls_hottest",
        )

        response = self.client.post(
            self.url,
            data=json.dumps({"code": code}),
            content_type="application/json",
            secure=True,
            HTTP_AUTHORIZATION=self.authorization,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "ok": True,
                "megaverse_user_ref": str(self.identity.public_id),
            },
        )

        authorization.refresh_from_db()
        self.assertIsNotNone(authorization.used_at)

    @override_settings(
        ALLOWED_HOSTS=["testserver"],
        MEGAVERSE_BRIDGE_API_KEY="test-bridge-secret",
    )
    def test_exchange_rejects_replayed_code(self):
        import json

        from integrations.models import MegaverseAuthorizationCode

        authorization, code = MegaverseAuthorizationCode.issue(
            identity=self.identity,
            destination="atls_hottest",
        )

        first_response = self.client.post(
            self.url,
            data=json.dumps({"code": code}),
            content_type="application/json",
            secure=True,
            HTTP_AUTHORIZATION=self.authorization,
        )

        second_response = self.client.post(
            self.url,
            data=json.dumps({"code": code}),
            content_type="application/json",
            secure=True,
            HTTP_AUTHORIZATION=self.authorization,
        )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 400)
        self.assertEqual(
            second_response.json()["error"],
            "invalid_authorization_code",
        )

    @override_settings(
        ALLOWED_HOSTS=["testserver"],
        MEGAVERSE_BRIDGE_API_KEY="test-bridge-secret",
    )
    def test_exchange_cannot_redeem_code_for_another_destination(self):
        import json

        from integrations.models import MegaverseAuthorizationCode

        authorization, code = MegaverseAuthorizationCode.issue(
            identity=self.identity,
            destination="another_destination",
        )

        response = self.client.post(
            self.url,
            data=json.dumps({"code": code}),
            content_type="application/json",
            secure=True,
            HTTP_AUTHORIZATION=self.authorization,
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["error"],
            "invalid_authorization_code",
        )

        authorization.refresh_from_db()
        self.assertIsNone(authorization.used_at)


class MegaverseBrowserAuthorizationTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        from django.urls import reverse

        User = get_user_model()

        self.user = User.objects.create_user(
            username="browser_bridge_user",
            email="browser-bridge@example.invalid",
            password="test-password-123",
        )

        self.client.force_login(self.user)
        self.url = reverse("authorize-atls-hottest")
        self.callback_url = (
            "https://app.atlshottest.com/megaverse/link/callback/"
        )
        self.state = "secure-browser-state-123"

    @override_settings(
        ALLOWED_HOSTS=["testserver"],
        ATL_HOTTEST_LINK_RETURN_URL="",
    )
    def test_authorization_fails_closed_without_callback_configuration(self):
        response = self.client.get(
            self.url,
            {"state": self.state},
            secure=True,
        )

        self.assertEqual(response.status_code, 503)
        self.assertContains(
            response,
            "connection has not been configured",
            status_code=503,
        )

    @override_settings(
        ALLOWED_HOSTS=["testserver"],
        ATL_HOTTEST_LINK_RETURN_URL=(
            "https://app.atlshottest.com/megaverse/link/callback/"
        ),
    )
    def test_get_displays_consent_without_issuing_code(self):
        from integrations.models import MegaverseAuthorizationCode

        response = self.client.get(
            self.url,
            {"state": self.state},
            secure=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Authorize Connection")
        self.assertFalse(
            MegaverseAuthorizationCode.objects.filter(
                identity__user=self.user,
                destination="atls_hottest",
            ).exists()
        )

    @override_settings(
        ALLOWED_HOSTS=["testserver"],
        ATL_HOTTEST_LINK_RETURN_URL=(
            "https://app.atlshottest.com/megaverse/link/callback/"
        ),
    )
    def test_authorize_issues_code_and_uses_only_fixed_callback(self):
        from urllib.parse import parse_qs, urlparse

        from integrations.models import (
            MegaverseAuthorizationCode,
            MegaverseIdentity,
        )

        response = self.client.post(
            self.url,
            {
                "state": self.state,
                "decision": "authorize",
                "return_url": "https://evil.example/steal",
            },
            secure=True,
        )

        self.assertEqual(response.status_code, 302)

        location = response["Location"]
        parsed = urlparse(location)
        params = parse_qs(parsed.query)

        self.assertEqual(
            f"{parsed.scheme}://{parsed.netloc}{parsed.path}",
            self.callback_url,
        )
        self.assertNotIn("evil.example", location)
        self.assertEqual(params.get("state"), [self.state])
        self.assertTrue(params.get("code", [""])[0])

        identity = MegaverseIdentity.objects.get(user=self.user)

        authorization = MegaverseAuthorizationCode.objects.get(
            identity=identity,
            destination="atls_hottest",
        )

        self.assertIsNone(authorization.used_at)

    @override_settings(
        ALLOWED_HOSTS=["testserver"],
        ATL_HOTTEST_LINK_RETURN_URL=(
            "https://app.atlshottest.com/megaverse/link/callback/"
        ),
    )
    def test_deny_returns_access_denied_without_issuing_code(self):
        from urllib.parse import parse_qs, urlparse

        from integrations.models import MegaverseAuthorizationCode

        response = self.client.post(
            self.url,
            {
                "state": self.state,
                "decision": "deny",
            },
            secure=True,
        )

        self.assertEqual(response.status_code, 302)

        params = parse_qs(urlparse(response["Location"]).query)

        self.assertEqual(params.get("error"), ["access_denied"])
        self.assertEqual(params.get("state"), [self.state])

        self.assertFalse(
            MegaverseAuthorizationCode.objects.filter(
                identity__user=self.user,
                destination="atls_hottest",
            ).exists()
        )

    @override_settings(
        ALLOWED_HOSTS=["testserver"],
        ATL_HOTTEST_LINK_RETURN_URL=(
            "https://app.atlshottest.com/megaverse/link/callback/"
        ),
    )
    def test_missing_state_is_rejected(self):
        response = self.client.get(
            self.url,
            secure=True,
        )

        self.assertEqual(response.status_code, 400)

    @override_settings(
        ALLOWED_HOSTS=["testserver"],
        ATL_HOTTEST_LINK_RETURN_URL=(
            "https://app.atlshottest.com/megaverse/link/callback/"
        ),
    )
    def test_inactive_identity_cannot_authorize(self):
        from integrations.models import (
            MegaverseAuthorizationCode,
            MegaverseIdentity,
        )

        identity = MegaverseIdentity.objects.create(
            user=self.user,
            is_active=False,
        )

        response = self.client.post(
            self.url,
            {
                "state": self.state,
                "decision": "authorize",
            },
            secure=True,
        )

        self.assertEqual(response.status_code, 403)

        self.assertFalse(
            MegaverseAuthorizationCode.objects.filter(
                identity=identity,
                destination="atls_hottest",
            ).exists()
        )
