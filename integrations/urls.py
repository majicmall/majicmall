from django.urls import path

from . import views

app_name = "integrations"

urlpatterns = [
    path("health/", views.bridge_health, name="bridge-health"),
    path(
        "identity/exchange/",
        views.exchange_identity_code,
        name="identity-exchange",
    ),
]
