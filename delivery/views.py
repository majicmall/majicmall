from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import DeliveryPartner, DeliveryJob


@login_required
def dashboard(request):
    partner = DeliveryPartner.objects.filter(user=request.user).first()

    if partner:
        available_jobs_qs = DeliveryJob.objects.filter(status="pending")

        if partner.current_zip:
            available_jobs_qs = available_jobs_qs.filter(
                delivery_zip=partner.current_zip
            )

        available_jobs = available_jobs_qs.order_by("-created_at")[:20]
        pending_jobs = available_jobs_qs.count()
    else:
        available_jobs = []
        pending_jobs = 0

    active_jobs = DeliveryJob.objects.filter(
        partner=partner,
        status__in=[
            "accepted",
            "picked_up",
            "out_for_delivery",
        ]
    ).count() if partner else 0

    completed_jobs = DeliveryJob.objects.filter(
        partner=partner,
        status="delivered"
    ).count() if partner else 0

    return render(
        request,
        "delivery/dashboard.html",
        {
            "partner": partner,
            "pending_jobs": pending_jobs,
            "active_jobs": active_jobs,
            "completed_jobs": completed_jobs,
            "available_jobs": available_jobs,
        },
    )