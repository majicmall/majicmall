from decimal import Decimal
from urllib.parse import quote_plus

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import DeliveryJob, DeliveryPartner


ACTIVE_JOB_STATUSES = {
    "accepted",
    "picked_up",
    "out_for_delivery",
}


def _driver_partner(request):
    return get_object_or_404(
        DeliveryPartner,
        user=request.user,
    )


def _driver_can_work(partner):
    return bool(
        partner.is_ready_for_command_center
        and partner.is_active
        and partner.approval_status == "approved"
    )


def _pickup_location(job):
    pickup_record = None

    try:
        from .pickup_models import MerchantPickupAddress

        pickup_record = (
            MerchantPickupAddress.objects
            .filter(store=job.store)
            .first()
        )
    except Exception:
        pickup_record = None

    if pickup_record and pickup_record.full_address:
        return {
            "address": pickup_record.full_address,
            "instructions": (
                pickup_record.pickup_instructions
                or job.pickup_notes
                or ""
            ),
            "is_exact": True,
        }

    store_name = (
        getattr(job.store, "store_name", "")
        or "Merchant Pickup"
    ).strip()

    pickup_zip = (
        getattr(job, "pickup_zip", "")
        or getattr(job.store, "business_zip", "")
        or ""
    ).strip()

    return {
        "address": ", ".join(
            value
            for value in [store_name, pickup_zip]
            if value
        ),
        "instructions": job.pickup_notes or "",
        "is_exact": False,
    }


def _dropoff_address(job):
    order = job.order

    parts = [
        getattr(order, "shipping_address", ""),
        getattr(order, "shipping_city", ""),
        getattr(order, "shipping_state", ""),
        getattr(order, "shipping_zip", ""),
    ]

    return ", ".join(
        str(value).strip()
        for value in parts
        if str(value or "").strip()
    )


def _google_maps_url(destination):
    return (
        "https://www.google.com/maps/dir/"
        f"?api=1&destination={quote_plus(destination or '')}"
    )


def _apple_maps_url(destination):
    return (
        "https://maps.apple.com/"
        f"?daddr={quote_plus(destination or '')}&dirflg=d"
    )


def _waze_url(destination):
    return (
        "https://www.waze.com/ul"
        f"?q={quote_plus(destination or '')}&navigate=yes"
    )


def _active_job_context(job):
    pickup = _pickup_location(job)
    dropoff_address = _dropoff_address(job)

    return {
        "job": job,
        "partner": job.partner,
        "order": job.order,
        "store": job.store,
        "pickup_address": pickup["address"],
        "pickup_instructions": pickup["instructions"],
        "pickup_address_is_exact": pickup["is_exact"],
        "dropoff_address": dropoff_address,
        "pickup_google_maps_url": _google_maps_url(
            pickup["address"]
        ),
        "pickup_apple_maps_url": _apple_maps_url(
            pickup["address"]
        ),
        "pickup_waze_url": _waze_url(
            pickup["address"]
        ),
        "dropoff_google_maps_url": _google_maps_url(
            dropoff_address
        ),
        "dropoff_apple_maps_url": _apple_maps_url(
            dropoff_address
        ),
        "dropoff_waze_url": _waze_url(
            dropoff_address
        ),
    }


def _refresh_partner_work_status(partner):
    has_active_jobs = DeliveryJob.objects.filter(
        partner=partner,
        status__in=ACTIVE_JOB_STATUSES,
    ).exists()

    partner.status = (
        "busy"
        if has_active_jobs
        else "available"
    )

    partner.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )


@login_required
def active_deliveries(request):
    partner = _driver_partner(request)

    jobs = (
        DeliveryJob.objects
        .filter(
            partner=partner,
            status__in=ACTIVE_JOB_STATUSES,
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

    return render(
        request,
        "delivery/active_deliveries.html",
        {
            "partner": partner,
            "active_jobs": jobs,
            "active_job_count": jobs.count(),
        },
    )


@login_required
@require_POST
def accept_delivery(request, job_id):
    partner = _driver_partner(request)

    if not _driver_can_work(partner):
        messages.error(
            request,
            (
                "Your driver account must be approved and active "
                "before accepting deliveries."
            ),
        )
        return redirect("delivery-dashboard")

    if partner.status != "available":
        messages.error(
            request,
            (
                "Complete or cancel your current active delivery "
                "before accepting another job."
            ),
        )
        return redirect("delivery-active-jobs")

    with transaction.atomic():
        job = get_object_or_404(
            DeliveryJob.objects.select_for_update(),
            pk=job_id,
        )

        if (
            job.status not in {"pending", "offered"}
            or job.partner_id is not None
        ):
            messages.error(
                request,
                "That delivery is no longer available.",
            )
            return redirect("delivery-dashboard")

        existing_active_job = (
            DeliveryJob.objects
            .select_for_update()
            .filter(
                partner=partner,
                status__in=ACTIVE_JOB_STATUSES,
            )
            .exists()
        )

        if existing_active_job:
            messages.error(
                request,
                (
                    "Complete or cancel your active delivery "
                    "before accepting another one."
                ),
            )
            return redirect("delivery-active-jobs")

        now = timezone.now()

        job.partner = partner
        job.status = "accepted"
        job.accepted_at = now
        job.save(
            update_fields=[
                "partner",
                "status",
                "accepted_at",
            ]
        )

        partner.status = "busy"
        partner.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        order = job.order

        if hasattr(order, "fulfillment_status"):
            order.fulfillment_status = "driver_assigned"
            order.save(
                update_fields=["fulfillment_status"]
            )

    messages.success(
        request,
        (
            f"Delivery #{job.id} accepted. "
            "Pickup navigation is ready."
        ),
    )

    return redirect(
        "delivery-active-job",
        job_id=job.id,
    )


@login_required
def active_delivery(request, job_id):
    partner = _driver_partner(request)

    job = get_object_or_404(
        DeliveryJob.objects.select_related(
            "partner",
            "store",
            "order",
        ),
        pk=job_id,
        partner=partner,
    )

    if job.status == "delivered":
        return redirect(
            "delivery-completed-job",
            job_id=job.id,
        )

    if job.status not in ACTIVE_JOB_STATUSES:
        messages.warning(
            request,
            "That delivery is not currently active.",
        )
        return redirect("delivery-active-jobs")

    return render(
        request,
        "delivery/active_delivery.html",
        _active_job_context(job),
    )


@login_required
@require_POST
def cancel_delivery(request, job_id):
    partner = _driver_partner(request)

    with transaction.atomic():
        job = get_object_or_404(
            DeliveryJob.objects.select_for_update(),
            pk=job_id,
            partner=partner,
        )

        if job.status != "accepted":
            messages.error(
                request,
                (
                    "This delivery can no longer be canceled because "
                    "the package has already entered the pickup or "
                    "delivery stage."
                ),
            )
            return redirect(
                "delivery-active-job",
                job_id=job.id,
            )

        order = job.order

        job.partner = None
        job.status = "pending"
        job.accepted_at = None

        job.save(
            update_fields=[
                "partner",
                "status",
                "accepted_at",
            ]
        )

        if hasattr(order, "fulfillment_status"):
            order.fulfillment_status = "driver_requested"
            order.save(
                update_fields=["fulfillment_status"]
            )

        _refresh_partner_work_status(partner)

    messages.success(
        request,
        (
            f"Delivery #{job.id} was canceled and returned "
            "to the available-delivery pool."
        ),
    )

    return redirect("delivery-active-jobs")


@login_required
@require_POST
def confirm_pickup(request, job_id):
    partner = _driver_partner(request)

    with transaction.atomic():
        job = get_object_or_404(
            DeliveryJob.objects.select_for_update(),
            pk=job_id,
            partner=partner,
        )

        if job.status != "accepted":
            messages.error(
                request,
                "This delivery cannot be marked picked up right now.",
            )
            return redirect(
                "delivery-active-job",
                job_id=job.id,
            )

        now = timezone.now()

        job.status = "picked_up"
        job.picked_up_at = now

        job.save(
            update_fields=[
                "status",
                "picked_up_at",
            ]
        )

        order = job.order
        update_fields = []

        if hasattr(order, "fulfillment_status"):
            order.fulfillment_status = "picked_up"
            update_fields.append("fulfillment_status")

        if hasattr(order, "shipping_status"):
            order.shipping_status = "picked_up"
            update_fields.append("shipping_status")

        if update_fields:
            order.save(update_fields=update_fields)

    messages.success(
        request,
        (
            "Package pickup confirmed. "
            "Customer navigation is now ready."
        ),
    )

    return redirect(
        "delivery-active-job",
        job_id=job.id,
    )


@login_required
@require_POST
def start_dropoff(request, job_id):
    partner = _driver_partner(request)

    with transaction.atomic():
        job = get_object_or_404(
            DeliveryJob.objects.select_for_update(),
            pk=job_id,
            partner=partner,
        )

        if job.status not in {
            "picked_up",
            "out_for_delivery",
        }:
            messages.error(
                request,
                "Confirm pickup before starting customer delivery.",
            )
            return redirect(
                "delivery-active-job",
                job_id=job.id,
            )

        if job.status == "picked_up":
            job.status = "out_for_delivery"
            job.save(update_fields=["status"])

            order = job.order
            update_fields = []

            if hasattr(order, "fulfillment_status"):
                order.fulfillment_status = "out_for_delivery"
                update_fields.append("fulfillment_status")

            if hasattr(order, "shipping_status"):
                order.shipping_status = "out_for_delivery"
                update_fields.append("shipping_status")

            if update_fields:
                order.save(update_fields=update_fields)

    return redirect(
        "delivery-active-job",
        job_id=job.id,
    )


@login_required
@require_POST
def confirm_delivery(request, job_id):
    partner = _driver_partner(request)

    with transaction.atomic():
        job = get_object_or_404(
            DeliveryJob.objects.select_for_update(),
            pk=job_id,
            partner=partner,
        )

        if job.status not in {
            "picked_up",
            "out_for_delivery",
        }:
            messages.error(
                request,
                (
                    "The package must be picked up before "
                    "delivery can be completed."
                ),
            )
            return redirect(
                "delivery-active-job",
                job_id=job.id,
            )

        now = timezone.now()

        payout = Decimal(
            job.total_driver_payout
            or Decimal("0.00")
        )

        job.status = "delivered"
        job.delivered_at = now

        job.save(
            update_fields=[
                "status",
                "delivered_at",
            ]
        )

        partner.completed_deliveries += 1
        partner.today_earnings += payout
        partner.weekly_earnings += payout

        partner.save(
            update_fields=[
                "completed_deliveries",
                "today_earnings",
                "weekly_earnings",
                "updated_at",
            ]
        )

        order = job.order
        update_fields = []

        if hasattr(order, "fulfillment_status"):
            order.fulfillment_status = "delivered"
            update_fields.append("fulfillment_status")

        if hasattr(order, "shipping_status"):
            order.shipping_status = "delivered"
            update_fields.append("shipping_status")

        if hasattr(order, "delivered_at"):
            order.delivered_at = now
            update_fields.append("delivered_at")

        if hasattr(order, "status"):
            order.status = "completed"
            update_fields.append("status")

        if update_fields:
            order.save(update_fields=update_fields)

        _refresh_partner_work_status(partner)

    messages.success(
        request,
        (
            f"Delivery #{job.id} completed successfully. "
            f"${payout:.2f} was added to your earnings."
        ),
    )

    return redirect(
        "delivery-completed-job",
        job_id=job.id,
    )


@login_required
def completed_delivery(request, job_id):
    partner = _driver_partner(request)

    job = get_object_or_404(
        DeliveryJob.objects.select_related(
            "partner",
            "store",
            "order",
        ),
        pk=job_id,
        partner=partner,
        status="delivered",
    )

    context = _active_job_context(job)
    context["driver_payout"] = job.total_driver_payout

    return render(
        request,
        "delivery/completed_delivery.html",
        context,
    )
