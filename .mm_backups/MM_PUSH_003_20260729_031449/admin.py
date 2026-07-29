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
