from __future__ import annotations

import json

from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from .auth import require_megaverse_bridge_auth
from .models import MegaverseAuthorizationCode


ATL_HOTTEST_DESTINATION = "atls_hottest"


@require_GET
@require_megaverse_bridge_auth
def bridge_health(request):
    """
    Authenticated MajicMall Megaverse integration health endpoint.

    Used by approved connected destinations to verify that the
    server-to-server bridge is configured and reachable.
    """
    return JsonResponse(
        {
            "ok": True,
            "service": "MajicMall Megaverse",
            "bridge": "integration",
            "version": 1,
        }
    )


@require_POST
@require_megaverse_bridge_auth
def exchange_identity_code(request):
    """
    Exchange a short-lived, single-use authorization code for the
    stable public MajicMall Megaverse identity reference.

    The destination is intentionally controlled by this server.
    Callers cannot choose or override it.

    No MajicMall Megaverse user PII is returned.
    """
    try:
        payload = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {
                "ok": False,
                "error": "invalid_request",
                "detail": "Request body must contain valid JSON.",
            },
            status=400,
        )

    if not isinstance(payload, dict):
        return JsonResponse(
            {
                "ok": False,
                "error": "invalid_request",
                "detail": "Request body must be a JSON object.",
            },
            status=400,
        )

    code = payload.get("code")

    if not isinstance(code, str) or not code.strip():
        return JsonResponse(
            {
                "ok": False,
                "error": "invalid_request",
                "detail": "A valid authorization code is required.",
            },
            status=400,
        )

    identity = MegaverseAuthorizationCode.redeem(
        code=code.strip(),
        destination=ATL_HOTTEST_DESTINATION,
    )

    if identity is None:
        return JsonResponse(
            {
                "ok": False,
                "error": "invalid_authorization_code",
                "detail": "Authorization code is invalid, expired, or already used.",
            },
            status=400,
        )

    return JsonResponse(
        {
            "ok": True,
            "megaverse_user_ref": str(identity.public_id),
        }
    )
