from django.test import SimpleTestCase, override_settings
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
