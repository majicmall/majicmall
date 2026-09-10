from __future__ import annotations

import secrets
from functools import wraps

from django.conf import settings
from django.http import JsonResponse


def require_megaverse_bridge_auth(view_func):
    """
    Require the MajicMall Megaverse server-to-server bridge credential.

    Expected header:
        Authorization: Bearer <MEGAVERSE_BRIDGE_API_KEY>

    Authentication fails closed if the server credential is not configured.
    """

    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        configured_key = getattr(settings, "MEGAVERSE_BRIDGE_API_KEY", "")

        if not configured_key:
            return JsonResponse(
                {
                    "error": "bridge_not_configured",
                    "detail": "MajicMall Megaverse integration bridge is not configured.",
                },
                status=503,
            )

        authorization = request.headers.get("Authorization", "")
        scheme, separator, supplied_key = authorization.partition(" ")

        if (
            not separator
            or scheme.lower() != "bearer"
            or not supplied_key
        ):
            return JsonResponse(
                {
                    "error": "unauthorized",
                    "detail": "Valid Bearer authentication is required.",
                },
                status=401,
            )

        if not secrets.compare_digest(supplied_key, configured_key):
            return JsonResponse(
                {
                    "error": "unauthorized",
                    "detail": "Invalid bridge credentials.",
                },
                status=401,
            )

        return view_func(request, *args, **kwargs)

    return wrapped_view
