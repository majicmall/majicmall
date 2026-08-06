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
        "inventory_tier",
        "minimum_spend",
        "featured",
        "active",
    )

    list_filter = (
        "property_type",
        "mall_zone",
        "availability_status",
        "inventory_tier",
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

from .models import PropertyLease


@admin.register(PropertyLease)
class PropertyLeaseAdmin(admin.ModelAdmin):
    list_display = (
        "lease_number",
        "merchant_store",
        "digital_property",
        "lease_plan",
        "status",
        "start_date",
        "end_date",
        "amount_paid",
        "auto_renew",
    )

    list_filter = (
        "status",
        "lease_plan",
        "digital_property__property_type",
        "digital_property__mall_zone",
        "auto_renew",
        "start_date",
        "end_date",
        "created_at",
    )

    search_fields = (
        "lease_number",
        "merchant_store__store_name",
        "merchant_store__owner__email",
        "digital_property__property_code",
        "digital_property__name",
        "campaign_name",
        "notes",
    )

    autocomplete_fields = (
        "merchant_store",
        "digital_property",
        "lease_plan",
    )

    readonly_fields = (
        "lease_number",
        "created_at",
        "updated_at",
        "duration_days_display",
    )

    ordering = (
        "-created_at",
    )

    date_hierarchy = "start_date"

    fieldsets = (
        (
            "Lease Identity",
            {
                "fields": (
                    "lease_number",
                    "status",
                ),
            },
        ),
        (
            "Merchant and Property",
            {
                "fields": (
                    "merchant_store",
                    "digital_property",
                    "lease_plan",
                ),
            },
        ),
        (
            "Lease Term",
            {
                "fields": (
                    "start_date",
                    "end_date",
                    "duration_days_display",
                    "auto_renew",
                ),
            },
        ),
        (
            "Financial Details",
            {
                "fields": (
                    "amount_paid",
                ),
            },
        ),
        (
            "Campaign Details",
            {
                "fields": (
                    "campaign_name",
                    "notes",
                ),
            },
        ),
        (
            "Audit",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
                "classes": (
                    "collapse",
                ),
            },
        ),
    )

    @admin.display(description="Duration")
    def duration_days_display(self, obj):
        if not obj or not obj.pk:
            return "Calculated after dates are selected"

        days = obj.duration_days
        return f"{days} day" if days == 1 else f"{days} days"

