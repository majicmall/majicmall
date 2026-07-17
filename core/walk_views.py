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
