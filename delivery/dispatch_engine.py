"""
MajicMall Megaverse Dispatch Engine.

Launch-safe responsibilities:

1. Determine whether approved Transport Partners are available.
2. Hide delivery jobs until the merchant releases the order.
3. Match ready jobs to the Transport Partner's working ZIP.
4. Preserve the existing navigation and delivery-completion workflow.
"""

from delivery.models import DeliveryJob, DeliveryPartner


DISPATCH_READY_ORDER_STATUSES = {
    "ready_for_pickup",
    "driver_requested",
    "driver_assigned",
}


ACTIVE_DELIVERY_STATUSES = {
    "accepted",
    "picked_up",
    "out_for_delivery",
}


def available_transport_partners(delivery_zip=None):
    partners = DeliveryPartner.objects.filter(
        approval_status="approved",
        is_active=True,
        onboarding_completed=True,
        contractor_agreement_accepted=True,
        status="available",
    )

    if delivery_zip:
        partners = partners.filter(
            current_zip=str(delivery_zip).strip(),
        )

    return partners


def transport_partner_coverage(delivery_zip=None):
    partners = available_transport_partners(delivery_zip)
    available_count = partners.count()

    if available_count >= 5:
        level = "excellent"
        label = "Excellent Coverage"
    elif available_count >= 2:
        level = "good"
        label = "Good Coverage"
    elif available_count == 1:
        level = "limited"
        label = "Limited Coverage"
    else:
        level = "offline"
        label = "Local Delivery Temporarily Unavailable"

    return {
        "available": available_count > 0,
        "available_count": available_count,
        "level": level,
        "label": label,
        "delivery_zip": str(delivery_zip or "").strip(),
    }


def order_is_dispatch_ready(order):
    fulfillment_status = str(
        getattr(order, "fulfillment_status", "") or ""
    ).strip().lower()

    return fulfillment_status in DISPATCH_READY_ORDER_STATUSES


def ready_delivery_jobs_for_partner(partner):
    """
    A job may appear in Available Deliveries only when:

    - it has not been assigned;
    - its delivery status is pending;
    - the merchant has released the order;
    - the destination matches the partner's active working ZIP.
    """
    if not partner or partner.status != "available":
        return DeliveryJob.objects.none()

    if not partner.current_zip:
        return DeliveryJob.objects.none()

    return (
        DeliveryJob.objects
        .filter(
            status="pending",
            partner__isnull=True,
            delivery_zip=partner.current_zip,
            order__fulfillment_status__in=(
                DISPATCH_READY_ORDER_STATUSES
            ),
        )
        .select_related(
            "store",
            "order",
        )
        .order_by(
            "created_at",
            "id",
        )
    )


def active_delivery_jobs_for_partner(partner):
    if not partner:
        return DeliveryJob.objects.none()

    return (
        DeliveryJob.objects
        .filter(
            partner=partner,
            status__in=ACTIVE_DELIVERY_STATUSES,
        )
        .select_related(
            "store",
            "order",
        )
        .order_by(
            "accepted_at",
            "id",
        )
    )
