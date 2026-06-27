from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import DeliveryPartner, DeliveryJob


@login_required
def dashboard(request):
    partner = DeliveryPartner.objects.filter(user=request.user).first()

    pending_jobs = DeliveryJob.objects.filter(status="pending").count()

    active_jobs = DeliveryJob.objects.filter(
        status__in=[
            "accepted",
            "picked_up",
            "out_for_delivery",
        ]
    ).count()

    completed_jobs = DeliveryJob.objects.filter(
        status="delivered"
    ).count()

    return render(
        request,
        "delivery/dashboard.html",
        {
            "partner": partner,
            "pending_jobs": pending_jobs,
            "active_jobs": active_jobs,
            "completed_jobs": completed_jobs,
        },
    )