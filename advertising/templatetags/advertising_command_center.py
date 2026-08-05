from decimal import Decimal

from django import template
from django.db.models import Sum
from django.utils import timezone

from advertising.models import AdvertisingCreative, Campaign
from digital_property.models import DigitalProperty, PropertyLease


register = template.Library()


def model_has_field(model, field_name):
    return any(
        field.name == field_name
        for field in model._meta.get_fields()
    )


def safe_status_count(queryset, model, status_value):
    if not model_has_field(model, "status"):
        return 0

    try:
        return queryset.filter(status=status_value).count()
    except Exception:
        return 0


@register.inclusion_tag(
    "advertising/includes/command_center_kpis.html",
)
def advertising_command_center_kpis():
    """
    Live executive statistics for the MajicMall Megaverse
    Digital Advertising Command Center.
    """

    today = timezone.localdate()

    properties = DigitalProperty.objects.all()
    leases = PropertyLease.objects.all()
    campaigns = Campaign.objects.all()
    creatives = AdvertisingCreative.objects.all()

    if model_has_field(DigitalProperty, "active"):
        properties = properties.filter(active=True)

    total_inventory = properties.count()

    available_inventory = safe_status_count(
        properties,
        DigitalProperty,
        "available",
    )

    reserved_inventory = safe_status_count(
        properties,
        DigitalProperty,
        "reserved",
    )

    leased_inventory = safe_status_count(
        properties,
        DigitalProperty,
        "leased",
    )

    active_leases = safe_status_count(
        leases,
        PropertyLease,
        "active",
    )

    pending_leases = safe_status_count(
        leases,
        PropertyLease,
        "pending",
    )

    active_campaigns = safe_status_count(
        campaigns,
        Campaign,
        "active",
    )

    pending_campaigns = safe_status_count(
        campaigns,
        Campaign,
        "pending",
    )

    # Support alternate campaign status terminology.
    if active_campaigns == 0:
        active_campaigns = safe_status_count(
            campaigns,
            Campaign,
            "running",
        )

    if pending_campaigns == 0:
        pending_campaigns = safe_status_count(
            campaigns,
            Campaign,
            "pending_approval",
        )

    if pending_campaigns == 0:
        pending_campaigns = safe_status_count(
            campaigns,
            Campaign,
            "submitted",
        )

    expiring_soon = 0

    if (
        model_has_field(PropertyLease, "end_date")
        and model_has_field(PropertyLease, "status")
    ):
        try:
            expiration_limit = today + timezone.timedelta(days=30)

            expiring_soon = leases.filter(
                status="active",
                end_date__gte=today,
                end_date__lte=expiration_limit,
            ).count()
        except Exception:
            expiring_soon = 0

    advertising_revenue = Decimal("0.00")

    if model_has_field(PropertyLease, "amount_paid"):
        try:
            revenue_queryset = leases

            if model_has_field(PropertyLease, "status"):
                revenue_queryset = revenue_queryset.filter(
                    status__in=[
                        "active",
                        "completed",
                        "expired",
                    ],
                )

            advertising_revenue = (
                revenue_queryset.aggregate(
                    total=Sum("amount_paid"),
                )["total"]
                or Decimal("0.00")
            )
        except Exception:
            advertising_revenue = Decimal("0.00")

    occupied_inventory = leased_inventory

    if occupied_inventory == 0 and active_leases:
        try:
            occupied_inventory = (
                leases.filter(status="active")
                .values("digital_property_id")
                .distinct()
                .count()
            )
        except Exception:
            occupied_inventory = active_leases

    occupancy_rate = 0

    if total_inventory:
        occupancy_rate = round(
            (occupied_inventory / total_inventory) * 100,
            1,
        )

    return {
        "total_inventory": total_inventory,
        "available_inventory": available_inventory,
        "reserved_inventory": reserved_inventory,
        "leased_inventory": leased_inventory,
        "active_leases": active_leases,
        "pending_leases": pending_leases,
        "total_campaigns": campaigns.count(),
        "active_campaigns": active_campaigns,
        "pending_campaigns": pending_campaigns,
        "total_creatives": creatives.count(),
        "expiring_soon": expiring_soon,
        "advertising_revenue": advertising_revenue,
        "occupancy_rate": occupancy_rate,
    }


@register.inclusion_tag(
    "advertising/includes/advertising_inventory.html",
)
def advertising_inventory_board():
    """
    Live advertising inventory for the Digital Advertising
    Command Center.
    """

    properties = (
        DigitalProperty.objects
        .select_related(
            "property_type",
            "mall_zone",
        )
        .prefetch_related(
            "lease_plans",
            "property_leases",
            "property_leases__merchant_store",
            "property_leases__lease_plan",
        )
        .order_by(
            "display_order",
            "name",
        )
    )

    if model_has_field(DigitalProperty, "active"):
        properties = properties.filter(active=True)

    inventory_items = []

    for property_item in properties:
        active_lease = None

        try:
            active_lease = (
                property_item.property_leases
                .filter(status="active")
                .order_by("-start_date", "-created_at")
                .first()
            )
        except Exception:
            active_lease = None

        advertiser_name = ""

        if active_lease and active_lease.merchant_store:
            merchant_store = active_lease.merchant_store

            advertiser_name = (
                getattr(merchant_store, "store_name", "")
                or getattr(merchant_store, "name", "")
                or str(merchant_store)
            )

        lease_plan_name = ""

        if active_lease and active_lease.lease_plan:
            lease_plan_name = (
                getattr(active_lease.lease_plan, "name", "")
                or str(active_lease.lease_plan)
            )

        zone_name = "Global"

        if property_item.mall_zone:
            zone_name = (
                getattr(property_item.mall_zone, "name", "")
                or str(property_item.mall_zone)
            )

        property_type_name = (
            getattr(property_item.property_type, "name", "")
            or str(property_item.property_type)
        )

        inventory_items.append(
            {
                "id": property_item.pk,
                "property_code": property_item.property_code,
                "name": property_item.name,
                "slug": property_item.slug,
                "description": property_item.description,
                "location_label": property_item.location_label,
                "property_type": property_type_name,
                "zone": zone_name,
                "status": property_item.availability_status,
                "status_label": property_item.get_availability_status_display(),
                "featured": property_item.featured,
                "supports_image": property_item.supports_image,
                "supports_video": property_item.supports_video,
                "interactive": property_item.interactive,
                "width": property_item.width,
                "height": property_item.height,
                "advertiser_name": advertiser_name,
                "lease_plan_name": lease_plan_name,
                "lease_end_date": (
                    active_lease.end_date
                    if active_lease
                    else None
                ),
            }
        )

    zones = sorted(
        {
            item["zone"]
            for item in inventory_items
            if item["zone"]
        }
    )

    property_types = sorted(
        {
            item["property_type"]
            for item in inventory_items
            if item["property_type"]
        }
    )

    return {
        "inventory_items": inventory_items,
        "inventory_count": len(inventory_items),
        "zones": zones,
        "property_types": property_types,
    }

