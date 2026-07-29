from django.contrib import admin
from .models import PropertyType, LeasePlan


@admin.register(PropertyType)
class PropertyTypeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "active",
        "created_at",
    )

    list_filter = (
        "active",
    )

    search_fields = (
        "name",
    )


@admin.register(LeasePlan)
class LeasePlanAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "billing_period",
        "price",
        "featured",
        "active",
    )

    list_filter = (
        "billing_period",
        "featured",
        "active",
    )

    search_fields = (
        "name",
    )

    ordering = (
        "display_order",
        "price",
    )

from .models import DigitalProperty



@admin.register(DigitalProperty)
class DigitalPropertyAdmin(admin.ModelAdmin):
    list_display = (
        "property_code",
        "name",
        "property_type",
        "mall_zone",
        "availability_status",
        "featured",
        "active",
    )

    list_filter = (
        "property_type",
        "mall_zone",
        "availability_status",
        "supports_image",
        "supports_video",
        "interactive",
        "featured",
        "active",
    )

    search_fields = (
        "property_code",
        "name",
        "slug",
        "description",
        "location_label",
    )

    filter_horizontal = ("lease_plans",)

    prepopulated_fields = {
        "slug": ("name",),
    }

    ordering = (
        "display_order",
        "name",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )
