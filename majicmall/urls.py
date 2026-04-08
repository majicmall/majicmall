from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from django.views.static import serve

from merchant.views import storefront, storefront_qr, product_detail


def healthz(request):
    return HttpResponse("OK", content_type="text/plain")


urlpatterns = [
    path("healthz/", healthz, name="healthz"),

    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),

    path("merchant/", include("merchant.urls")),
    path("theater/", include("theater.urls")),
    path("", include("core.urls")),

    # Public storefront URLs
    path("store/<slug:slug>/", storefront, name="storefront"),
    path("store/<slug:slug>/products/<int:product_id>/", product_detail, name="product-detail"),
    path("store/<slug:slug>/qr.png", storefront_qr, name="storefront-qr"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if not settings.DEBUG:
    urlpatterns += [
        re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
    ]