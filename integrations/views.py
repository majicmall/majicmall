from __future__ import annotations

from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .auth import require_megaverse_bridge_auth


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
