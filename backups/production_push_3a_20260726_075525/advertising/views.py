from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CampaignForm
from .models import AdvertisingCreative, Campaign


def dashboard(request):
    context = {
        "campaigns": Campaign.objects.count(),
        "active_campaigns": Campaign.objects.filter(status="active").count(),
        "creatives": AdvertisingCreative.objects.count(),
        "approved": AdvertisingCreative.objects.filter(
            approval_status="approved"
        ).count(),
    }

    return render(request, "advertising/dashboard.html", context)


def campaign_list(request):
    campaigns = Campaign.objects.all()

    search_query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip()

    campaign_field_names = {
        field.name for field in Campaign._meta.get_fields()
    }

    if search_query:
        searchable_fields = [
            field_name
            for field_name in (
                "name",
                "title",
                "campaign_name",
                "description",
                "advertiser_name",
            )
            if field_name in campaign_field_names
        ]

        search_conditions = Q()

        for field_name in searchable_fields:
            search_conditions |= Q(
                **{f"{field_name}__icontains": search_query}
            )

        if searchable_fields:
            campaigns = campaigns.filter(search_conditions)

    if status_filter and "status" in campaign_field_names:
        campaigns = campaigns.filter(status=status_filter)

    ordering_candidates = (
        "-created_at",
        "-created",
        "-date_created",
        "-id",
    )

    for ordering in ordering_candidates:
        if ordering.lstrip("-") in campaign_field_names:
            campaigns = campaigns.order_by(ordering)
            break

    status_choices = []

    try:
        status_field = Campaign._meta.get_field("status")
        status_choices = list(status_field.choices)
    except Exception:
        status_choices = []

    context = {
        "campaigns": campaigns,
        "search_query": search_query,
        "status_filter": status_filter,
        "status_choices": status_choices,
        "total_campaigns": Campaign.objects.count(),
        "active_campaigns": (
            Campaign.objects.filter(status="active").count()
            if "status" in campaign_field_names
            else 0
        ),
        "campaign_fields": campaign_field_names,
    }

    return render(
        request,
        "advertising/campaign_list.html",
        context,
    )


def campaign_create(request):
    if request.method == "POST":
        form = CampaignForm(request.POST, request.FILES)

        if form.is_valid():
            campaign = form.save()

            messages.success(
                request,
                f'Campaign "{campaign}" was created successfully.',
            )

            return redirect("advertising:campaign_list")
    else:
        form = CampaignForm()

    return render(
        request,
        "advertising/campaign_form.html",
        {
            "form": form,
            "page_title": "Create Campaign",
            "page_subtitle": (
                "Build a new advertising campaign for the "
                "MajicMall Megaverse Media Network."
            ),
            "submit_label": "Create Campaign",
        },
    )


def campaign_edit(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)

    if request.method == "POST":
        form = CampaignForm(
            request.POST,
            request.FILES,
            instance=campaign,
        )

        if form.is_valid():
            campaign = form.save()

            messages.success(
                request,
                f'Campaign "{campaign}" was updated successfully.',
            )

            return redirect("advertising:campaign_list")
    else:
        form = CampaignForm(instance=campaign)

    return render(
        request,
        "advertising/campaign_form.html",
        {
            "form": form,
            "campaign": campaign,
            "page_title": "Edit Campaign",
            "page_subtitle": (
                "Update campaign settings, timing and network details."
            ),
            "submit_label": "Save Changes",
        },
    )


def campaign_delete(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)

    if request.method == "POST":
        campaign_name = str(campaign)
        campaign.delete()

        messages.success(
            request,
            f'Campaign "{campaign_name}" was deleted.',
        )

        return redirect("advertising:campaign_list")

    return render(
        request,
        "advertising/campaign_confirm_delete.html",
        {"campaign": campaign},
    )
