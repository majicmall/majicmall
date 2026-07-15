from django.urls import path

from . import dispatch_views
from . import pickup_address_views
from . import views
from . import workflow_views


urlpatterns = [
    # ==============================================================
    # MajicMall Megaverse Transport Partner Command Center
    # ==============================================================
    path(
        "",
        dispatch_views.dashboard,
        name="delivery-dashboard",
    ),

    # ==============================================================
    # Transport Partner Registration, Authentication, and Onboarding
    # ==============================================================
    path(
        "become-a-driver/",
        views.become_driver,
        name="delivery-become-driver",
    ),
    path(
        "signup/",
        views.driver_signup,
        name="delivery-driver-signup",
    ),
    path(
        "sign-up/",
        views.driver_signup,
        name="delivery-driver-signup-alias",
    ),
    path(
        "sign-in/",
        views.DriverLoginView.as_view(),
        name="delivery-driver-login",
    ),
    path(
        "sign-out/",
        views.driver_logout,
        name="delivery-driver-logout",
    ),
    path(
        "onboarding/",
        views.driver_onboarding,
        name="delivery-onboarding",
    ),
    path(
        "status/",
        views.update_driver_status,
        name="delivery-update-status",
    ),

    # ==============================================================
    # Merchant Operational Pickup Location
    # ==============================================================
    path(
        "merchant-pickup-address/",
        pickup_address_views.merchant_pickup_address,
        name="merchant-pickup-address",
    ),

    # ==============================================================
    # Active Delivery Manager
    # ==============================================================
    path(
        "jobs/active/",
        workflow_views.active_deliveries,
        name="delivery-active-jobs",
    ),

    # ==============================================================
    # Transport Partner Delivery Workflow
    # ==============================================================
    path(
        "jobs/<int:job_id>/accept/",
        workflow_views.accept_delivery,
        name="delivery-accept-job",
    ),
    path(
        "jobs/<int:job_id>/active/",
        workflow_views.active_delivery,
        name="delivery-active-job",
    ),
    path(
        "jobs/<int:job_id>/cancel/",
        workflow_views.cancel_delivery,
        name="delivery-cancel-job",
    ),
    path(
        "jobs/<int:job_id>/confirm-pickup/",
        workflow_views.confirm_pickup,
        name="delivery-confirm-pickup",
    ),
    path(
        "jobs/<int:job_id>/start-dropoff/",
        workflow_views.start_dropoff,
        name="delivery-start-dropoff",
    ),
    path(
        "jobs/<int:job_id>/confirm-delivery/",
        workflow_views.confirm_delivery,
        name="delivery-confirm-delivery",
    ),
    path(
        "jobs/<int:job_id>/completed/",
        workflow_views.completed_delivery,
        name="delivery-completed-job",
    ),
]
