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
