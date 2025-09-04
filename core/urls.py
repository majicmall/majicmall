# core/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Homepage & splash
    path("", views.homepage, name="home"),
    path("mall/", views.mall_home, name="mall-home"),
    path("splash/", views.launch_splash, name="launch-splash"),

    # Directory & invites
    path("directory/", views.mall_directory, name="mall-directory"),
    path("merchant/invite/", views.merchant_invite, name="merchant-invite"),

    # Merchant onboarding (marketing flow pages can stay in core)
    path("merchant-onboard/", views.merchant_onboard, name="merchant-onboard"),
    path("merchant-thank-you/", views.merchant_thank_you, name="merchant-thank-you"),

    # Zones
    path("zone/fashion/", views.fashion_zone, name="fashion-zone"),
    path("zone/entertainment/", views.entertainment_zone, name="entertainment-zone"),
    path("zone/tech/", views.tech_zone, name="tech-zone"),
    path("zone/home/", views.home_zone, name="home-zone"),
    path("zone/family/", views.family_zone, name="family-zone"),
    path("zone/creators/", views.creators_zone, name="creators-zone"),
    path("zone/luxury/", views.luxury_zone, name="luxury-zone"),
    path("zone/atls-hottest/", views.atls_hottest_zone, name="atls-hottest-zone"),
    path("zone/food/", views.food_court_zone, name="food-court-zone"),
    path("zone/theater/", views.theater_zone, name="theater-zone"),
    path("zone/learning/", views.learning_zone, name="learning-zone"),

    # TV
    path("tv/", views.tv_home, name="tv-home"),
]
