from django.contrib import admin

from .models import DeliveryJob, DeliveryPartner


@admin.register(DeliveryPartner)
class DeliveryPartnerAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "status",
        "vehicle_type",
        "home_zip",
        "current_zip",
        "address_verified",
        "service_radius_miles",
        "rating",
        "completed_deliveries",
        "onboarding_completed",
        "contractor_agreement_accepted",
        "address_verified",
        "is_active",
    )

    list_filter = (
        "status",
        "vehicle_type",
        "onboarding_completed",
        "contractor_agreement_accepted",
        "is_active",
        "created_at",
    )

    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "user__email",
        "phone",
        "street_address",
        "city",
        "state",
        "home_zip",
        "current_zip",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "contractor_agreement_accepted_at",
        "address_verified_at",
        "onboarding_completed_at",
    )

    fieldsets = (
        (
            "Driver Account",
            {
                "fields": (
                    "user",
                    "is_active",
                    "onboarding_completed",
                    "onboarding_completed_at",
                )
            },
        ),
        (
            "Verified Residential Address",
            {
                "fields": (
                    "street_address",
                    "address_line_2",
                    "city",
                    "state",
                    "home_zip",
                    "address_verified",
                    "address_verified_at",
                )
            },
        ),
        (
            "Service Area",
            {
                "fields": (
                    "current_zip",
                    "service_radius_miles",
                )
            },
        ),
        (
            "Driver Details",
            {
                "fields": (
                    "phone",
                    "vehicle_type",
                    "status",
                )
            },
        ),
        (
            "Performance",
            {
                "fields": (
                    "rating",
                    "completed_deliveries",
                    "today_earnings",
                    "weekly_earnings",
                )
            },
        ),
        (
            "Independent Contractor Agreement",
            {
                "fields": (
                    "contractor_agreement_accepted",
                    "contractor_agreement_version",
                    "contractor_agreement_accepted_at",
                )
            },
        ),
        (
            "System Information",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )


@admin.register(DeliveryJob)
class DeliveryJobAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order",
        "store",
        "partner",
        "status",
        "pickup_zip",
        "delivery_zip",
        "delivery_fee",
        "tip_amount",
        "created_at",
    )

    list_filter = (
        "status",
        "pickup_zip",
        "delivery_zip",
        "created_at",
    )

    search_fields = (
        "order__id",
        "store__store_name",
        "partner__user__username",
        "pickup_zip",
        "delivery_zip",
    )

    readonly_fields = (
        "created_at",
        "accepted_at",
        "picked_up_at",
        "delivered_at",
    )
