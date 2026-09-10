from __future__ import annotations

import json
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from .auth import require_megaverse_bridge_auth
from .models import MegaverseAuthorizationCode, MegaverseIdentity


ATL_HOTTEST_DESTINATION = "atls_hottest"


def _callback_with_params(callback_url, **params):
    """
    Add trusted handoff parameters to the fixed callback URL.
    """
    parts = urlsplit(callback_url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.update(params)

    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            parts.path,
            urlencode(query),
            parts.fragment,
        )
    )


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


@login_required
@never_cache
@require_http_methods(["GET", "POST"])
def authorize_atls_hottest(request):
    """
    Allow a signed-in MajicMall Megaverse account holder to explicitly
    authorize connection of their stable identity to ATL's Hottest.
    """
    callback_url = settings.ATL_HOTTEST_LINK_RETURN_URL

    if not callback_url:
        return render(
            request,
            "integrations/authorize_atls_hottest.html",
            {
                "configuration_error": True,
            },
            status=503,
        )

    if request.method == "POST":
        state = (request.POST.get("state") or "").strip()
    else:
        state = (request.GET.get("state") or "").strip()

    if not state or len(state) > 255:
        return render(
            request,
            "integrations/authorize_atls_hottest.html",
            {
                "request_error": True,
            },
            status=400,
        )

    if request.method == "POST":
        decision = request.POST.get("decision")

        if decision == "deny":
            return redirect(
                _callback_with_params(
                    callback_url,
                    error="access_denied",
                    state=state,
                )
            )

        if decision != "authorize":
            return render(
                request,
                "integrations/authorize_atls_hottest.html",
                {
                    "request_error": True,
                },
                status=400,
            )

        identity, _ = MegaverseIdentity.objects.get_or_create(
            user=request.user,
        )

        if not identity.is_active:
            return render(
                request,
                "integrations/authorize_atls_hottest.html",
                {
                    "identity_inactive": True,
                },
                status=403,
            )

        _, code = MegaverseAuthorizationCode.issue(
            identity=identity,
            destination=ATL_HOTTEST_DESTINATION,
            lifetime_seconds=300,
        )

        return redirect(
            _callback_with_params(
                callback_url,
                code=code,
                state=state,
            )
        )

    display_name = (
        request.user.get_full_name().strip()
        or request.user.username
    )

    return render(
        request,
        "integrations/authorize_atls_hottest.html",
        {
            "state": state,
            "display_name": display_name,
        },
    )
