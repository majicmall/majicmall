from django.shortcuts import render
from .models import Campaign, AdvertisingCreative


def dashboard(request):
    context = {
        "campaigns": Campaign.objects.count(),
        "active_campaigns": Campaign.objects.filter(status="active").count(),
        "creatives": AdvertisingCreative.objects.count(),
        "approved": AdvertisingCreative.objects.filter(
            approval_status="approved"
        ).count(),
    }

    return render(
        request,
        "advertising/dashboard.html",
        context,
    )
