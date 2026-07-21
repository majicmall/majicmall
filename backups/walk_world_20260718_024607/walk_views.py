from django.shortcuts import get_object_or_404, render

from merchant.models import MallZone, MerchantStore


def walk_zone(request, zone_slug):
    zone = get_object_or_404(
        MallZone,
        slug=zone_slug,
    )

    stores = list(
        MerchantStore.objects.filter(
            zone=zone,
            is_public=True,
            is_archived=False,
        )
        .exclude(slug="")
        .order_by("store_name")
    )

    return render(
        request,
        "mall/walk_zone.html",
        {
            "zone": zone,
            "stores": stores,
        },
    )


def walk_zone_v2(request, zone_slug):
    """
    Safe architectural preview of Walk the Mall 2.0.

    The original walk_zone experience remains unchanged while
    the permanent luxury environment is developed separately.
    """
    zone = get_object_or_404(
        MallZone,
        slug=zone_slug,
    )

    stores = list(
        MerchantStore.objects.filter(
            zone=zone,
            is_public=True,
            is_archived=False,
        )
        .exclude(slug="")
        .order_by("store_name")
    )

    return render(
        request,
        "mall/walk_zone_v2.html",
        {
            "zone": zone,
            "stores": stores,
        },
    )


# WALK THE MALL ENGINE V2 — CLEAN ARCHITECTURAL VIEW
def walk_zone_engine_v2(request, zone_slug):
    """
    Clean-room Walk the Mall architecture engine.

    This view does not use or modify the original Walk the Mall
    template or its motion engine.
    """
    zone = get_object_or_404(
        MallZone,
        slug=zone_slug,
    )

    stores = (
        MerchantStore.objects.filter(
            zone=zone,
            is_public=True,
            is_archived=False,
        )
        .exclude(slug="")
        .order_by("store_name")
    )

    return render(
        request,
        "mall/walk_zone_engine_v2.html",
        {
            "zone": zone,
            "stores": stores,
        },
    )
# END WALK THE MALL ENGINE V2 VIEW

