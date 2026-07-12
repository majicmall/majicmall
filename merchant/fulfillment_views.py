from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from delivery.models import DeliveryJob

from .models import (
    MerchantFulfillmentSettings,
    MerchantStore,
    Order,
)


ACTIVE_STORE_SESSION_KEYS = (
    "active_store_id",
    "merchant_store_id",
    "selected_store_id",
    "current_store_id",
)


def _merchant_store_for_request(request):
    stores = MerchantStore.objects.filter(
        owner=request.user,
        is_archived=False,
    )

    for session_key in ACTIVE_STORE_SESSION_KEYS:
        store_id = request.session.get(session_key)

        if store_id:
            selected = stores.filter(pk=store_id).first()

            if selected:
                return selected

    return stores.order_by("created_at").first()


def _settings_for_store(store):
    settings_obj, _created = (
        MerchantFulfillmentSettings.objects.get_or_create(
            store=store
        )
    )

    return settings_obj


def _merchant_order_or_404(request, order_id):
    store = _merchant_store_for_request(request)

    if not store:
        return None, None

    order = get_object_or_404(
        Order.objects.select_related("store").prefetch_related("items"),
        pk=order_id,
        store=store,
    )

    return store, order


def _dispatch_delivery_job(order):
    if order.fulfillment_method != "local_delivery":
        return None

    job, _created = DeliveryJob.objects.get_or_create(
        order=order,
        defaults={
            "store": order.store,
            "status": "pending",
            "pickup_zip": (
                getattr(order.store, "business_zip", "") or ""
            ),
            "delivery_zip": order.shipping_zip or "",
            "delivery_fee": (
                getattr(order.store, "delivery_fee", 0) or 0
            ),
            "delivery_notes": order.delivery_notes or "",
        },
    )

    update_fields = []

    if job.store_id != order.store_id:
        job.store = order.store
        update_fields.append("store")

    if job.status in {"offered", "canceled"}:
        job.status = "pending"
        update_fields.append("status")

    pickup_zip = (
        getattr(order.store, "business_zip", "") or ""
    )

    if job.pickup_zip != pickup_zip:
        job.pickup_zip = pickup_zip
        update_fields.append("pickup_zip")

    if job.delivery_zip != (order.shipping_zip or ""):
        job.delivery_zip = order.shipping_zip or ""
        update_fields.append("delivery_zip")

    if update_fields:
        job.save(update_fields=update_fields)

    return job


@login_required
def fulfillment_center(request):
    store = _merchant_store_for_request(request)

    if not store:
        messages.info(
            request,
            "Create a merchant store to open the Fulfillment Center.",
        )
        return redirect("merchant-onboard")

    fulfillment_settings = _settings_for_store(store)

    orders = (
        store.orders
        .select_related("delivery_job")
        .prefetch_related("items")
        .order_by("-created_at")
    )

    awaiting_orders = orders.filter(
        status__in=["paid", "completed"],
        fulfillment_status="awaiting_acceptance",
    )

    active_orders = orders.filter(
        fulfillment_status__in=[
            "accepted",
            "preparing",
            "picking",
            "packing",
            "ready_for_pickup",
            "driver_requested",
            "driver_assigned",
            "customer_pickup_ready",
            "shipped",
            "out_for_delivery",
        ]
    )

    completed_orders = orders.filter(
        fulfillment_status__in=[
            "fulfilled",
            "declined",
            "canceled",
        ]
    )[:20]

    return render(
        request,
        "merchant/fulfillment/center.html",
        {
            "store": store,
            "fulfillment_settings": fulfillment_settings,
            "awaiting_orders": awaiting_orders,
            "active_orders": active_orders,
            "completed_orders": completed_orders,
            "awaiting_count": awaiting_orders.count(),
            "active_count": active_orders.count(),
        },
    )


@login_required
@require_POST
def update_availability(request):
    store = _merchant_store_for_request(request)

    if not store:
        messages.error(request, "No merchant store was found.")
        return redirect("merchant-dashboard")

    fulfillment_settings = _settings_for_store(store)

    requested_status = (
        request.POST.get("availability_status", "")
        .strip()
        .lower()
    )

    allowed = {
        value
        for value, _label
        in MerchantFulfillmentSettings.AVAILABILITY_CHOICES
    }

    if requested_status not in allowed:
        messages.error(request, "Invalid availability status.")
        return redirect("merchant-fulfillment-center")

    fulfillment_settings.availability_status = requested_status
    fulfillment_settings.pause_message = (
        request.POST.get("pause_message", "").strip()
    )
    fulfillment_settings.save(
        update_fields=[
            "availability_status",
            "pause_message",
            "last_status_change_at",
        ]
    )

    messages.success(
        request,
        (
            f"{store.store_name} is now "
            f"{fulfillment_settings.get_availability_status_display()}."
        ),
    )

    return redirect("merchant-fulfillment-center")


@login_required
@require_POST
def update_notification_preferences(request):
    store = _merchant_store_for_request(request)

    if not store:
        messages.error(request, "No merchant store was found.")
        return redirect("merchant-dashboard")

    fulfillment_settings = _settings_for_store(store)

    fulfillment_settings.sound_alerts_enabled = (
        request.POST.get("sound_alerts_enabled") == "on"
    )
    fulfillment_settings.browser_notifications_enabled = (
        request.POST.get("browser_notifications_enabled") == "on"
    )
    fulfillment_settings.email_alerts_enabled = (
        request.POST.get("email_alerts_enabled") == "on"
    )

    merchant_type = (
        request.POST.get("merchant_type", "")
        .strip()
        .lower()
    )

    allowed_types = {
        value
        for value, _label
        in MerchantFulfillmentSettings.MERCHANT_TYPE_CHOICES
    }

    if merchant_type in allowed_types:
        fulfillment_settings.merchant_type = merchant_type

    try:
        minutes = int(
            request.POST.get("default_preparation_minutes", 15)
        )
    except (TypeError, ValueError):
        minutes = 15

    fulfillment_settings.default_preparation_minutes = max(
        1,
        min(minutes, 1440),
    )

    fulfillment_settings.save()

    messages.success(
        request,
        "Fulfillment alert preferences updated.",
    )

    return redirect("merchant-fulfillment-center")


@login_required
@require_POST
def accept_order(request, order_id):
    store, order = _merchant_order_or_404(request, order_id)

    if not store:
        messages.error(request, "No merchant store was found.")
        return redirect("merchant-dashboard")

    if order.status not in {"paid", "completed"}:
        messages.error(
            request,
            "Only paid orders can enter fulfillment.",
        )
        return redirect("merchant-fulfillment-center")

    fulfillment_settings = _settings_for_store(store)

    try:
        ready_minutes = int(
            request.POST.get(
                "ready_minutes",
                fulfillment_settings.default_preparation_minutes,
            )
        )
    except (TypeError, ValueError):
        ready_minutes = (
            fulfillment_settings.default_preparation_minutes
        )

    ready_minutes = max(1, min(ready_minutes, 1440))
    now = timezone.now()

    if fulfillment_settings.merchant_type in {
        "restaurant",
        "florist",
    }:
        next_status = "preparing"
    else:
        next_status = "picking"

    order.fulfillment_status = next_status
    order.merchant_response_at = now
    order.alert_acknowledged_at = now
    order.estimated_ready_at = now + timedelta(
        minutes=ready_minutes
    )
    order.fulfillment_updated_at = now
    order.rejection_reason = ""

    order.save(
        update_fields=[
            "fulfillment_status",
            "merchant_response_at",
            "alert_acknowledged_at",
            "estimated_ready_at",
            "fulfillment_updated_at",
            "rejection_reason",
        ]
    )

    messages.success(
        request,
        (
            f"Order #{order.id} accepted. "
            f"Estimated ready time: {ready_minutes} minutes."
        ),
    )

    return redirect("merchant-fulfillment-center")


@login_required
@require_POST
def decline_order(request, order_id):
    store, order = _merchant_order_or_404(request, order_id)

    if not store:
        messages.error(request, "No merchant store was found.")
        return redirect("merchant-dashboard")

    reason = request.POST.get("rejection_reason", "").strip()
    now = timezone.now()

    order.fulfillment_status = "declined"
    order.merchant_response_at = now
    order.alert_acknowledged_at = now
    order.fulfillment_updated_at = now
    order.rejection_reason = reason

    order.save(
        update_fields=[
            "fulfillment_status",
            "merchant_response_at",
            "alert_acknowledged_at",
            "fulfillment_updated_at",
            "rejection_reason",
        ]
    )

    if hasattr(order, "delivery_job"):
        job = order.delivery_job

        if job.status in {"pending", "offered"}:
            job.status = "canceled"
            job.save(update_fields=["status"])

    messages.warning(
        request,
        f"Order #{order.id} was declined.",
    )

    return redirect("merchant-fulfillment-center")


@login_required
@require_POST
def update_fulfillment_status(request, order_id):
    store, order = _merchant_order_or_404(request, order_id)

    if not store:
        messages.error(request, "No merchant store was found.")
        return redirect("merchant-dashboard")

    requested_status = (
        request.POST.get("fulfillment_status", "")
        .strip()
        .lower()
    )

    allowed = {
        "accepted",
        "preparing",
        "picking",
        "packing",
        "ready_for_pickup",
        "customer_pickup_ready",
        "shipped",
        "out_for_delivery",
        "fulfilled",
    }

    if requested_status not in allowed:
        messages.error(request, "Invalid fulfillment status.")
        return redirect("merchant-fulfillment-center")

    now = timezone.now()

    order.fulfillment_status = requested_status
    order.fulfillment_updated_at = now

    update_fields = [
        "fulfillment_status",
        "fulfillment_updated_at",
    ]

    if requested_status in {
        "ready_for_pickup",
        "customer_pickup_ready",
    }:
        order.ready_for_pickup_at = now
        update_fields.append("ready_for_pickup_at")

    if requested_status == "ready_for_pickup":
        if order.fulfillment_method == "local_delivery":
            job = _dispatch_delivery_job(order)

            if job:
                order.fulfillment_status = "driver_requested"
                update_fields[0] = "fulfillment_status"

    if requested_status == "fulfilled":
        if order.status != "completed":
            order.status = "completed"
            update_fields.append("status")

    order.save(update_fields=update_fields)

    messages.success(
        request,
        (
            f"Order #{order.id} updated to "
            f"{order.get_fulfillment_status_display()}."
        ),
    )

    return redirect("merchant-fulfillment-center")


@login_required
@require_POST
def acknowledge_order_alert(request, order_id):
    store, order = _merchant_order_or_404(request, order_id)

    if not store:
        return JsonResponse(
            {"ok": False, "error": "Store not found."},
            status=404,
        )

    if not order.alert_acknowledged_at:
        order.alert_acknowledged_at = timezone.now()
        order.save(update_fields=["alert_acknowledged_at"])

    return JsonResponse({"ok": True})


@login_required
@require_GET
def fulfillment_alert_feed(request):
    store = _merchant_store_for_request(request)

    if not store:
        return JsonResponse(
            {
                "ok": False,
                "orders": [],
                "count": 0,
            }
        )

    fulfillment_settings = _settings_for_store(store)

    orders = (
        store.orders
        .filter(
            status__in=["paid", "completed"],
            fulfillment_status="awaiting_acceptance",
        )
        .prefetch_related("items")
        .order_by("created_at")[:10]
    )

    payload = []

    for order in orders:
        payload.append(
            {
                "id": order.id,
                "customer_name": (
                    order.customer_name or "MajicMall Megaverse Customer"
                ),
                "total": str(order.total),
                "fulfillment_method": order.fulfillment_method,
                "created_at": order.created_at.isoformat(),
                "detail_url": reverse(
                    "order-detail",
                    kwargs={"order_id": order.id},
                ),
            }
        )

    return JsonResponse(
        {
            "ok": True,
            "count": len(payload),
            "orders": payload,
            "sound_enabled": (
                fulfillment_settings.sound_alerts_enabled
            ),
            "browser_notifications_enabled": (
                fulfillment_settings.browser_notifications_enabled
            ),
        }
    )


@login_required
def fulfillment_order_detail(request, order_id):
    store, order = _merchant_order_or_404(request, order_id)

    if not store:
        messages.info(
            request,
            "Create a merchant store to manage fulfillment.",
        )
        return redirect("merchant-dashboard")

    fulfillment_settings = _settings_for_store(store)

    delivery_job = getattr(order, "delivery_job", None)

    if order.fulfillment_method == "pickup":
        workflow_label = "Customer Pickup"
        ready_action_label = "Mark Customer Pickup Ready"
        ready_status = "customer_pickup_ready"
    elif order.fulfillment_method == "local_delivery":
        workflow_label = "MajicMall Megaverse Driver Network"
        ready_action_label = "Ready for Driver Pickup"
        ready_status = "ready_for_pickup"
    else:
        workflow_label = "Merchant Shipping"
        ready_action_label = "Mark Shipped"
        ready_status = "shipped"

    return render(
        request,
        "merchant/fulfillment/order.html",
        {
            "store": store,
            "order": order,
            "fulfillment_settings": fulfillment_settings,
            "delivery_job": delivery_job,
            "workflow_label": workflow_label,
            "ready_action_label": ready_action_label,
            "ready_status": ready_status,
        },
    )
