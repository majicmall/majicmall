from django.urls import path

from . import views

app_name = "advertising"

urlpatterns = [
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
