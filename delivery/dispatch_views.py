from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render

from .dispatch_engine import (
    active_delivery_jobs_for_partner,
    ready_delivery_jobs_for_partner,
    transport_partner_coverage,
)
from .models import DeliveryJob, DeliveryPartner


@login_required
def dashboard(request):
    partner = (
        DeliveryPartner.objects
        .filter(user=request.user)
        .first()
    )

    available_jobs = DeliveryJob.objects.none()
    active_delivery_jobs = DeliveryJob.objects.none()
    completed_delivery_jobs = DeliveryJob.objects.none()

    pending_jobs = 0
    active_jobs = 0
    completed_jobs = 0

    coverage = {
        "available": False,
        "available_count": 0,
        "level": "offline",
        "label": "Local Delivery Temporarily Unavailable",
        "delivery_zip": "",
    }

    if partner and partner.is_ready_for_command_center:
        coverage = transport_partner_coverage(
            partner.current_zip
        )

        available_jobs = ready_delivery_jobs_for_partner(
            partner
        )

        active_delivery_jobs = (
            active_delivery_jobs_for_partner(partner)
        )

        completed_delivery_jobs = (
            DeliveryJob.objects
            .filter(
                partner=partner,
                status="delivered",
            )
            .select_related(
                "store",
                "order",
            )
            .order_by(
                "-delivered_at",
                "-id",
            )
        )

        pending_jobs = available_jobs.count()
        active_jobs = active_delivery_jobs.count()
        completed_jobs = completed_delivery_jobs.count()

    return render(
        request,
        "delivery/dashboard.html",
        {
            "partner": partner,
            "coverage": coverage,
            "pending_jobs": pending_jobs,
            "active_jobs": active_jobs,
            "completed_jobs": completed_jobs,
            "available_jobs": available_jobs,
            "active_delivery_jobs": active_delivery_jobs,
            "completed_delivery_jobs": (
                completed_delivery_jobs[:10]
            ),
        },
    )
