from django.urls import path

from . import views


urlpatterns = [
    path(
        "",
        views.dashboard,
        name="delivery-dashboard",
    ),
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
]
