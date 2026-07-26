from django.shortcuts import render

from .models import AdvertisingCreative, Campaign


def dashboard(request):
    """
    MajicMall Media Network executive dashboard.

    The department modules are currently presented as visual command-center
    cards. Individual module pages will be connected as each system is built.
    """

    context = {
        "campaigns": Campaign.objects.count(),
        "active_campaigns": Campaign.objects.filter(status="active").count(),
        "creatives": AdvertisingCreative.objects.count(),
        "approved": AdvertisingCreative.objects.filter(
            approval_status="approved"
        ).count(),
    }

    return render(request, "advertising/dashboard.html", context)
