from .forms import AdvertisingCreativeForm
from django.urls import reverse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CampaignForm, DigitalPropertyForm
from .models import AdvertisingCreative, Campaign, CampaignPlacement
from digital_property.models import DigitalProperty


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



def campaign_detail(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)

    creatives = campaign.creatives.all().order_by("-created_at")

    context = {
        "campaign": campaign,
        "creatives": creatives,
        "creative_count": creatives.count(),
        "approved_count": creatives.filter(
            approval_status=AdvertisingCreative.ApprovalStatus.APPROVED
        ).count(),
        "pending_count": creatives.filter(
            approval_status=AdvertisingCreative.ApprovalStatus.PENDING
        ).count(),
        "draft_count": creatives.filter(
            approval_status=AdvertisingCreative.ApprovalStatus.DRAFT
        ).count(),
        "rejected_count": creatives.filter(
            approval_status=AdvertisingCreative.ApprovalStatus.REJECTED
        ).count(),
        "placements": campaign.placements.select_related(
            "digital_property",
            "lease_plan",
            "digital_property__mall_zone",
        ),
    }

    return render(
        request,
        "advertising/campaign_detail.html",
        context,
    )


def campaign_create(request):
    submit_action = request.POST.get("submit_action", "draft")

    if request.method == "POST":
        form = CampaignForm(
            request.POST,
            request.FILES,
            user=request.user,
            submit_action=submit_action,
        )

        if form.is_valid():
            campaign = form.save()

            if submit_action == "submit":
                messages.success(
                    request,
                    f'Campaign "{campaign}" was submitted for approval.',
                )

                return redirect(
                    "advertising:campaign_detail",
                    pk=campaign.pk,
                )

            if submit_action == "upload":
                messages.success(
                    request,
                    (
                        f'Campaign "{campaign}" was saved. '
                        "Upload your creative now."
                    ),
                )

                return redirect(
                    "advertising:campaign-creative-create",
                    campaign_id=campaign.pk,
                )

            messages.success(
                request,
                f'Campaign "{campaign}" was saved as a draft.',
            )

            return redirect(
                "advertising:campaign_edit",
                pk=campaign.pk,
            )
    else:
        form = CampaignForm(
            user=request.user,
            submit_action="draft",
        )

    return render(
        request,
        "advertising/campaign_form.html",
        {
            "form": form,
            "page_title": "Create Campaign",
            "page_subtitle": (
                "Choose advertising locations, lease terms, dates, "
                "budget and creative support."
            ),
            "campaign": None,
        },
    )


def campaign_edit(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    submit_action = request.POST.get("submit_action", "draft")

    if request.method == "POST":
        form = CampaignForm(
            request.POST,
            request.FILES,
            instance=campaign,
            user=request.user,
            submit_action=submit_action,
        )

        if form.is_valid():
            campaign = form.save()

            if submit_action == "submit":
                messages.success(
                    request,
                    f'Campaign "{campaign}" was submitted for approval.',
                )

                return redirect(
                    "advertising:campaign_detail",
                    pk=campaign.pk,
                )

            if submit_action == "upload":
                messages.success(
                    request,
                    (
                        f'Campaign "{campaign}" was saved. '
                        "Upload your creative now."
                    ),
                )

                return redirect(
                    "advertising:campaign-creative-create",
                    campaign_id=campaign.pk,
                )

            messages.success(
                request,
                f'Campaign "{campaign}" was saved as a draft.',
            )

            return redirect(
                "advertising:campaign_edit",
                pk=campaign.pk,
            )
    else:
        form = CampaignForm(
            instance=campaign,
            user=request.user,
            submit_action="draft",
        )

    return render(
        request,
        "advertising/campaign_form.html",
        {
            "form": form,
            "campaign": campaign,
            "page_title": "Edit Campaign",
            "page_subtitle": (
                "Update campaign placements, lease plan, dates, "
                "budget and submission status."
            ),
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


def media_network_dashboard(request):
    """
    MajicMall Megaverse Media Network headquarters.
    """

    campaign_model = None
    creative_model = None

    try:
        from .models import Campaign
        campaign_model = Campaign
    except (ImportError, AttributeError):
        pass

    try:
        from .models import AdvertisingCreative
        creative_model = AdvertisingCreative
    except (ImportError, AttributeError):
        pass

    campaign_queryset = None
    campaign_count = 0
    active_campaign_count = 0
    paused_campaign_count = 0
    draft_campaign_count = 0
    recent_campaigns = []

    if campaign_model is not None:
        try:
            campaign_queryset = campaign_model.objects.all()
            campaign_count = campaign_queryset.count()

            status_field = None

            try:
                status_field = campaign_model._meta.get_field("status")
            except Exception:
                status_field = None

            if status_field is not None:
                active_campaign_count = campaign_queryset.filter(
                    status__iexact="active"
                ).count()

                paused_campaign_count = campaign_queryset.filter(
                    status__iexact="paused"
                ).count()

                draft_campaign_count = campaign_queryset.filter(
                    status__iexact="draft"
                ).count()

            ordering_field = None

            for candidate in (
                "updated_at",
                "modified_at",
                "created_at",
                "id",
                "pk",
            ):
                try:
                    campaign_model._meta.get_field(candidate)
                    ordering_field = candidate
                    break
                except Exception:
                    continue

            if ordering_field:
                recent_campaigns = list(
                    campaign_queryset.order_by(
                        f"-{ordering_field}"
                    )[:5]
                )
            else:
                recent_campaigns = list(campaign_queryset[:5])

        except Exception:
            campaign_count = 0
            active_campaign_count = 0
            paused_campaign_count = 0
            draft_campaign_count = 0
            recent_campaigns = []

    creative_count = 0

    if creative_model is not None:
        try:
            creative_count = creative_model.objects.count()
        except Exception:
            creative_count = 0

    context = {
        "campaign_count": campaign_count,
        "active_campaign_count": active_campaign_count,
        "paused_campaign_count": paused_campaign_count,
        "draft_campaign_count": draft_campaign_count,
        "creative_count": creative_count,
        "recent_campaigns": recent_campaigns,
    }

    return render(
        request,
        "advertising/media_network_dashboard.html",
        context,
    )




@login_required
def creative_studio(request):
    creatives = AdvertisingCreative.objects.all()

    campaign_field_exists = False

    try:
        AdvertisingCreative._meta.get_field("campaign")
        campaign_field_exists = True
    except Exception:
        campaign_field_exists = False

    ordering = None

    for candidate in (
        "updated_at",
        "modified_at",
        "created_at",
        "id",
        "pk",
    ):
        try:
            AdvertisingCreative._meta.get_field(candidate)
            ordering = candidate
            break
        except Exception:
            continue

    if ordering:
        creatives = creatives.order_by(f"-{ordering}")

    context = {
        "creatives": creatives,
        "creative_count": creatives.count(),
        "campaign_field_exists": campaign_field_exists,
    }

    return render(
        request,
        "advertising/creative_studio.html",
        context,
    )


@login_required
def creative_create(request, campaign_id=None):
    campaign = None

    if campaign_id is not None:
        campaign = get_object_or_404(
            Campaign,
            pk=campaign_id,
        )

    submit_action = request.POST.get(
        "submit_action",
        "draft",
    )

    if request.method == "POST":
        form = AdvertisingCreativeForm(
            request.POST,
            request.FILES,
            campaign=campaign,
            user=request.user,
        )

        if form.is_valid():
            creative = form.save(
                submit_for_review=(
                    submit_action == "submit"
                ),
            )

            if submit_action == "submit":
                messages.success(
                    request,
                    "Creative submitted for approval.",
                )
            else:
                messages.success(
                    request,
                    "Creative saved as a draft.",
                )

            return redirect(
                "advertising:campaign_detail",
                pk=creative.campaign_id,
            )
    else:
        form = AdvertisingCreativeForm(
            campaign=campaign,
            user=request.user,
        )

    return render(
        request,
        "advertising/creative_form.html",
        {
            "form": form,
            "campaign": campaign,
        },
    )


def staff_required(user):
    return user.is_authenticated and user.is_staff


@user_passes_test(staff_required)
def inventory_manager(request):
    properties = (
        DigitalProperty.objects
        .select_related("property_type", "mall_zone")
        .prefetch_related("lease_plans")
        .order_by("display_order", "name")
    )

    return render(
        request,
        "advertising/inventory_manager.html",
        {
            "properties": properties,
        },
    )


@user_passes_test(staff_required)
def inventory_create(request):
    if request.method == "POST":
        form = DigitalPropertyForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():
            property_item = form.save()

            messages.success(
                request,
                (
                    f'Advertising inventory "{property_item.name}" '
                    "was created."
                ),
            )

            return redirect(
                "advertising:inventory-manager",
            )
    else:
        form = DigitalPropertyForm()

    return render(
        request,
        "advertising/inventory_form.html",
        {
            "form": form,
            "page_title": "Add Advertising Inventory",
            "submit_label": "Create Inventory",
        },
    )


@user_passes_test(staff_required)
def inventory_edit(request, pk):
    property_item = get_object_or_404(
        DigitalProperty,
        pk=pk,
    )

    if request.method == "POST":
        form = DigitalPropertyForm(
            request.POST,
            request.FILES,
            instance=property_item,
        )

        if form.is_valid():
            property_item = form.save()

            messages.success(
                request,
                (
                    f'Advertising inventory "{property_item.name}" '
                    "was updated."
                ),
            )

            return redirect(
                "advertising:inventory-manager",
            )
    else:
        form = DigitalPropertyForm(
            instance=property_item,
        )

    return render(
        request,
        "advertising/inventory_form.html",
        {
            "form": form,
            "property_item": property_item,
            "page_title": "Edit Advertising Inventory",
            "submit_label": "Save Inventory",
        },
    )


@login_required
def carole_creative_studio(request):
    campaign = None
    campaign_id = (
        request.POST.get("campaign")
        or request.GET.get("campaign")
    )

    if campaign_id:
        campaign = get_object_or_404(
            Campaign,
            pk=campaign_id,
        )

    creative_brief = None

    if request.method == "POST":
        promotion = request.POST.get(
            "promotion",
            "",
        ).strip()

        audience = request.POST.get(
            "audience",
            "",
        ).strip()

        offer = request.POST.get(
            "offer",
            "",
        ).strip()

        tone = request.POST.get(
            "tone",
            "Luxury and confident",
        ).strip()

        headline = (
            f"Discover {promotion}"
            if promotion
            else "Discover Something Majestic"
        )

        call_to_action = (
            "Shop Now"
            if "sale" in offer.lower()
            or "discount" in offer.lower()
            else "Learn More"
        )

        creative_brief = {
            "headline": headline,
            "supporting_copy": (
                f"Created for {audience or 'MajicMall Megaverse visitors'} "
                f"with a {tone.lower()} presentation."
            ),
            "offer": offer or "Highlight the campaign's strongest benefit.",
            "call_to_action": call_to_action,
            "recommended_format": (
                "Use a bold focal image, short headline, high contrast, "
                "and one clear call to action."
            ),
        }

    return render(
        request,
        "advertising/carole_creative_studio.html",
        {
            "campaign": campaign,
            "creative_brief": creative_brief,
        },
    )



# =========================================================
# MM_PUSH_005E — Approval and scheduling operations
# =========================================================

from django.views.decorators.http import require_POST

from .services import (
    approve_campaign,
    reject_campaign,
    request_campaign_changes,
    sync_campaign_states,
)


@user_passes_test(staff_required)
def approval_center(request):
    sync_result = sync_campaign_states()

    pending_campaigns = (
        Campaign.objects
        .filter(status=Campaign.Status.PENDING)
        .prefetch_related(
            "placements",
            "placements__digital_property",
            "placements__lease_plan",
            "creatives",
        )
        .order_by("created_at")
    )

    scheduled_campaigns = (
        Campaign.objects
        .filter(status=Campaign.Status.SCHEDULED)
        .prefetch_related(
            "placements",
            "placements__digital_property",
        )
        .order_by("start_at")
    )

    active_campaigns = (
        Campaign.objects
        .filter(status=Campaign.Status.ACTIVE)
        .prefetch_related(
            "placements",
            "placements__digital_property",
        )
        .order_by("end_at")
    )

    context = {
        "pending_campaigns": pending_campaigns,
        "scheduled_campaigns": scheduled_campaigns,
        "active_campaigns": active_campaigns,
        "pending_count": pending_campaigns.count(),
        "scheduled_count": scheduled_campaigns.count(),
        "active_count": active_campaigns.count(),
        "sync_result": sync_result,
    }

    return render(
        request,
        "advertising/approval_center.html",
        context,
    )


@user_passes_test(staff_required)
def campaign_review(request, pk):
    sync_campaign_states()

    campaign = get_object_or_404(
        Campaign.objects.prefetch_related(
            "placements",
            "placements__digital_property",
            "placements__lease_plan",
            "creatives",
        ),
        pk=pk,
    )

    return render(
        request,
        "advertising/campaign_review.html",
        {
            "campaign": campaign,
            "placements": campaign.placements.all(),
            "creatives": campaign.creatives.all(),
        },
    )


@require_POST
@user_passes_test(staff_required)
def campaign_approve(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    review_notes = request.POST.get(
        "review_notes",
        "",
    ).strip()

    try:
        approve_campaign(
            campaign,
            reviewed_by=request.user,
            review_notes=review_notes,
        )
    except ValueError as exc:
        messages.error(request, str(exc))

        return redirect(
            "advertising:campaign-review",
            pk=campaign.pk,
        )

    messages.success(
        request,
        (
            f'Campaign "{campaign.name}" was approved and '
            "its advertising inventory was scheduled."
        ),
    )

    return redirect(
        "advertising:approval-center",
    )


@require_POST
@user_passes_test(staff_required)
def campaign_request_changes(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    review_notes = request.POST.get(
        "review_notes",
        "",
    ).strip()

    if not review_notes:
        messages.error(
            request,
            "Enter the changes the advertiser must make.",
        )

        return redirect(
            "advertising:campaign-review",
            pk=campaign.pk,
        )

    request_campaign_changes(
        campaign,
        reviewed_by=request.user,
        review_notes=review_notes,
    )

    messages.success(
        request,
        (
            f'Changes were requested for campaign '
            f'"{campaign.name}".'
        ),
    )

    return redirect(
        "advertising:approval-center",
    )


@require_POST
@user_passes_test(staff_required)
def campaign_reject(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    review_notes = request.POST.get(
        "review_notes",
        "",
    ).strip()

    if not review_notes:
        messages.error(
            request,
            "Enter a rejection reason.",
        )

        return redirect(
            "advertising:campaign-review",
            pk=campaign.pk,
        )

    reject_campaign(
        campaign,
        reviewed_by=request.user,
        review_notes=review_notes,
    )

    messages.success(
        request,
        f'Campaign "{campaign.name}" was rejected.',
    )

    return redirect(
        "advertising:approval-center",
    )


# =========================================================
# MM_PUSH_005E — Approval and scheduling operations
# =========================================================

from django.views.decorators.http import require_POST

from .services import (
    approve_campaign,
    reject_campaign,
    request_campaign_changes,
    sync_campaign_states,
)


@user_passes_test(staff_required)
def approval_center(request):
    sync_result = sync_campaign_states()

    pending_campaigns = (
        Campaign.objects
        .filter(status=Campaign.Status.PENDING)
        .prefetch_related(
            "placements",
            "placements__digital_property",
            "placements__lease_plan",
            "creatives",
        )
        .order_by("created_at")
    )

    scheduled_campaigns = (
        Campaign.objects
        .filter(status=Campaign.Status.SCHEDULED)
        .prefetch_related(
            "placements",
            "placements__digital_property",
        )
        .order_by("start_at")
    )

    active_campaigns = (
        Campaign.objects
        .filter(status=Campaign.Status.ACTIVE)
        .prefetch_related(
            "placements",
            "placements__digital_property",
        )
        .order_by("end_at")
    )

    context = {
        "pending_campaigns": pending_campaigns,
        "scheduled_campaigns": scheduled_campaigns,
        "active_campaigns": active_campaigns,
        "pending_count": pending_campaigns.count(),
        "scheduled_count": scheduled_campaigns.count(),
        "active_count": active_campaigns.count(),
        "sync_result": sync_result,
    }

    return render(
        request,
        "advertising/approval_center.html",
        context,
    )


@user_passes_test(staff_required)
def campaign_review(request, pk):
    sync_campaign_states()

    campaign = get_object_or_404(
        Campaign.objects.prefetch_related(
            "placements",
            "placements__digital_property",
            "placements__lease_plan",
            "creatives",
        ),
        pk=pk,
    )

    return render(
        request,
        "advertising/campaign_review.html",
        {
            "campaign": campaign,
            "placements": campaign.placements.all(),
            "creatives": campaign.creatives.all(),
        },
    )


@require_POST
@user_passes_test(staff_required)
def campaign_approve(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    review_notes = request.POST.get(
        "review_notes",
        "",
    ).strip()

    try:
        approve_campaign(
            campaign,
            reviewed_by=request.user,
            review_notes=review_notes,
        )
    except ValueError as exc:
        messages.error(request, str(exc))

        return redirect(
            "advertising:campaign-review",
            pk=campaign.pk,
        )

    messages.success(
        request,
        (
            f'Campaign "{campaign.name}" was approved and '
            "its advertising inventory was scheduled."
        ),
    )

    return redirect(
        "advertising:approval-center",
    )


@require_POST
@user_passes_test(staff_required)
def campaign_request_changes(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    review_notes = request.POST.get(
        "review_notes",
        "",
    ).strip()

    if not review_notes:
        messages.error(
            request,
            "Enter the changes the advertiser must make.",
        )

        return redirect(
            "advertising:campaign-review",
            pk=campaign.pk,
        )

    request_campaign_changes(
        campaign,
        reviewed_by=request.user,
        review_notes=review_notes,
    )

    messages.success(
        request,
        (
            f'Changes were requested for campaign '
            f'"{campaign.name}".'
        ),
    )

    return redirect(
        "advertising:approval-center",
    )


@require_POST
@user_passes_test(staff_required)
def campaign_reject(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    review_notes = request.POST.get(
        "review_notes",
        "",
    ).strip()

    if not review_notes:
        messages.error(
            request,
            "Enter a rejection reason.",
        )

        return redirect(
            "advertising:campaign-review",
            pk=campaign.pk,
        )

    reject_campaign(
        campaign,
        reviewed_by=request.user,
        review_notes=review_notes,
    )

    messages.success(
        request,
        f'Campaign "{campaign.name}" was rejected.',
    )

    return redirect(
        "advertising:approval-center",
    )


# =========================================================
# MM_PUSH_005E — Approval and scheduling operations
# =========================================================

from django.views.decorators.http import require_POST

from .services import (
    approve_campaign,
    reject_campaign,
    request_campaign_changes,
    sync_campaign_states,
)


@user_passes_test(staff_required)
def approval_center(request):
    sync_result = sync_campaign_states()

    pending_campaigns = (
        Campaign.objects
        .filter(status=Campaign.Status.PENDING)
        .prefetch_related(
            "placements",
            "placements__digital_property",
            "placements__lease_plan",
            "creatives",
        )
        .order_by("created_at")
    )

    scheduled_campaigns = (
        Campaign.objects
        .filter(status=Campaign.Status.SCHEDULED)
        .prefetch_related(
            "placements",
            "placements__digital_property",
        )
        .order_by("start_at")
    )

    active_campaigns = (
        Campaign.objects
        .filter(status=Campaign.Status.ACTIVE)
        .prefetch_related(
            "placements",
            "placements__digital_property",
        )
        .order_by("end_at")
    )

    context = {
        "pending_campaigns": pending_campaigns,
        "scheduled_campaigns": scheduled_campaigns,
        "active_campaigns": active_campaigns,
        "pending_count": pending_campaigns.count(),
        "scheduled_count": scheduled_campaigns.count(),
        "active_count": active_campaigns.count(),
        "sync_result": sync_result,
    }

    return render(
        request,
        "advertising/approval_center.html",
        context,
    )


@user_passes_test(staff_required)
def campaign_review(request, pk):
    sync_campaign_states()

    campaign = get_object_or_404(
        Campaign.objects.prefetch_related(
            "placements",
            "placements__digital_property",
            "placements__lease_plan",
            "creatives",
        ),
        pk=pk,
    )

    return render(
        request,
        "advertising/campaign_review.html",
        {
            "campaign": campaign,
            "placements": campaign.placements.all(),
            "creatives": campaign.creatives.all(),
        },
    )


@require_POST
@user_passes_test(staff_required)
def campaign_approve(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    review_notes = request.POST.get(
        "review_notes",
        "",
    ).strip()

    try:
        approve_campaign(
            campaign,
            reviewed_by=request.user,
            review_notes=review_notes,
        )
    except ValueError as exc:
        messages.error(request, str(exc))

        return redirect(
            "advertising:campaign-review",
            pk=campaign.pk,
        )

    messages.success(
        request,
        (
            f'Campaign "{campaign.name}" was approved and '
            "its advertising inventory was scheduled."
        ),
    )

    return redirect(
        "advertising:approval-center",
    )


@require_POST
@user_passes_test(staff_required)
def campaign_request_changes(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    review_notes = request.POST.get(
        "review_notes",
        "",
    ).strip()

    if not review_notes:
        messages.error(
            request,
            "Enter the changes the advertiser must make.",
        )

        return redirect(
            "advertising:campaign-review",
            pk=campaign.pk,
        )

    request_campaign_changes(
        campaign,
        reviewed_by=request.user,
        review_notes=review_notes,
    )

    messages.success(
        request,
        (
            f'Changes were requested for campaign '
            f'"{campaign.name}".'
        ),
    )

    return redirect(
        "advertising:approval-center",
    )


@require_POST
@user_passes_test(staff_required)
def campaign_reject(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    review_notes = request.POST.get(
        "review_notes",
        "",
    ).strip()

    if not review_notes:
        messages.error(
            request,
            "Enter a rejection reason.",
        )

        return redirect(
            "advertising:campaign-review",
            pk=campaign.pk,
        )

    reject_campaign(
        campaign,
        reviewed_by=request.user,
        review_notes=review_notes,
    )

    messages.success(
        request,
        f'Campaign "{campaign.name}" was rejected.',
    )

    return redirect(
        "advertising:approval-center",
    )
