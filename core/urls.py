from django.urls import path
from . import views

urlpatterns = [
    # ---------------------------
    # 🌍 Global Pages
    # ---------------------------
    path("", views.homepage, name="home"),
    path("enter/", views.mall_entrance, name="mall-entrance"),
    path("mall/", views.mall_home, name="mall-home"),
    path("splash/", views.launch_splash, name="launch-splash"),
    path("community/signup/", views.community_signup, name="community-signup"),
    path("grand-entrance-city-view/", views.grand_entrance_city_view, name="grand-entrance-city-view"),
    path("grand-reveal/", views.grand_reveal, name="grand-reveal"),

    # ---------------------------
    # 🗺️ Mall Directory
    # ---------------------------
    path("directory/", views.mall_directory, name="mall-directory"),

    # ---------------------------
    # 🏬 ZONES
    # ---------------------------
    path("zones/<slug:zone_slug>/", views.zone_entry, name="zone-entry"),
    path("zones/<slug:zone_slug>/inside/", views.zone_interior, name="zone-interior"),

    # ---------------------------
    # 💼 Merchant Flow
    # ---------------------------
    path("merchant/invite/", views.merchant_invite, name="merchant-invite"),
    path("merchant-onboard/", views.merchant_onboard, name="merchant-onboard"),
    path("merchant-thank-you/", views.merchant_thank_you, name="merchant-thank-you"),

    # ---------------------------
    # 📺 TV
    # ---------------------------
    path("tv/", views.tv_home, name="tv-home"),

    # ---------------------------
    # 🎬 Theater
    # ---------------------------
    path("theater/", views.theater_zone, name="theater-zone"),
]