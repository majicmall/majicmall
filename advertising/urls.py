from django.urls import path

from . import views

app_name = "advertising"

urlpatterns = [

    path(
        "display/live/<str:property_code>/",
        views.live_billboard_feed,
        name="live-billboard-feed",
    ),

    path(
        "approvals/",
        views.approval_center,
        name="approval-center",
    ),
    path(
        "approvals/<int:pk>/",
        views.campaign_review,
        name="campaign-review",
    ),
    path(
        "approvals/<int:pk>/approve/",
        views.campaign_approve,
        name="campaign-approve",
    ),
    path(
        "approvals/<int:pk>/request-changes/",
        views.campaign_request_changes,
        name="campaign-request-changes",
    ),
    path(
        "approvals/<int:pk>/reject/",
        views.campaign_reject,
        name="campaign-reject",
    ),
    path(
        "inventory/",
        views.inventory_manager,
        name="inventory-manager",
    ),
    path(
        "inventory/create/",
        views.inventory_create,
        name="inventory-create",
    ),
    path(
        "inventory/<int:pk>/edit/",
        views.inventory_edit,
        name="inventory-edit",
    ),
    path(
        "carole/",
        views.carole_creative_studio,
        name="carole-creative-studio",
    ),
    path(
        "creatives/",
        views.creative_studio,
        name="creative-studio",
    ),
    path(
        "creatives/create/",
        views.creative_create,
        name="creative-create",
    ),
    path(
        "campaigns/<int:campaign_id>/creatives/create/",
        views.creative_create,
        name="campaign-creative-create",
    ),
    path("", views.media_network_dashboard, name="media-network-dashboard"),
    path("", views.dashboard, name="dashboard"),

    path(
        "campaigns/",
        views.campaign_list,
        name="campaign_list",
    ),

    path(
        "campaigns/create/",
        views.campaign_create,
        name="campaign_create",
    ),

    path(
        "campaigns/<int:pk>/",
        views.campaign_detail,
        name="campaign_detail",
    ),

    path(
        "campaigns/<int:pk>/edit/",
        views.campaign_edit,
        name="campaign_edit",
    ),

    path(
        "campaigns/<int:pk>/delete/",
        views.campaign_delete,
        name="campaign_delete",
    ),
]
