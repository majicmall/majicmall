# majicmall/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse

# storefront + qr endpoints
from merchant.views import storefront, storefront_qr


# --- Health check (prevents Render from killing the service) ---
def healthz(request):
    return HttpResponse("OK", content_type="text/plain")


urlpatterns = [
    # Health check (must be FIRST)
    path("healthz/", healthz, name="healthz"),

    # Admin & auth
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),

    # App routes
    path("merchant/", include("merchant.urls")),
    path("theater/", include("theater.urls")),
    path("", include("core.urls")),

    # Public storefront + QR
    path("s/<slug:slug>/", storefront, name="storefront"),
    path("s/<slug:slug>/qr.png", storefront_qr, name="storefront-qr"),
]

# Local media/static serving (dev only)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

