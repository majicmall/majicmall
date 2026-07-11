from django.contrib import admin, messages
from django.utils import timezone
from django.utils.html import format_html

from .models import DeliveryJob, DeliveryPartner


@admin.action(description="Approve selected drivers")
def approve_drivers(modeladmin, request, queryset):
    now = timezone.now()
    updated = 0

    for partner in queryset:
        partner.approval_status = "approved"
        partner.reviewed_at = now
        partner.reviewed_by = request.user
        partner.is_active = True
        partner.deactivated_at = None

        if partner.status not in {"offline", "available", "busy"}:
            partner.status = "offline"

        partner.save(
            update_fields=[
                "approval_status",
                "reviewed_at",
                "reviewed_by",
                "is_active",
                "deactivated_at",
                "status",
                "updated_at",
            ]
        )
        updated += 1

    modeladmin.message_user(
        request,
        f"{updated} driver account(s) approved and activated.",
        level=messages.SUCCESS,
    )


@admin.action(description="Reject selected driver applications")
def reject_drivers(modeladmin, request, queryset):
    now = timezone.now()

    updated = queryset.update(
        approval_status="rejected",
        reviewed_at=now,
        reviewed_by=request.user,
        is_active=False,
        status="offline",
        deactivated_at=now,
    )

    modeladmin.message_user(
        request,
        f"{updated} driver application(s) rejected.",
        level=messages.WARNING,
    )


@admin.action(description="Activate selected approved drivers")
def activate_drivers(modeladmin, request, queryset):
    approved_queryset = queryset.filter(
        approval_status="approved"
    )

    updated = approved_queryset.update(
        is_active=True,
        deactivated_at=None,
        status="offline",
    )

    skipped = queryset.count() - updated

    message = f"{updated} approved driver account(s) activated."

    if skipped:
        message += (
            f" {skipped} account(s) were skipped because they "
            "have not been approved."
        )

    modeladmin.message_user(
        request,
        message,
        level=messages.SUCCESS,
    )


@admin.action(description="Deactivate selected drivers")
def deactivate_drivers(modeladmin, request, queryset):
    now = timezone.now()

    updated = queryset.update(
        is_active=False,
        status="offline",
        deactivated_at=now,
    )

    modeladmin.message_user(
        request,
        f"{updated} driver account(s) deactivated.",
        level=messages.WARNING,
    )


@admin.register(DeliveryPartner)
class DeliveryPartnerAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "approval_status",
        "is_active",
        "onboarding_completed",
        "address_verified",
        "verification_complete",
        "status",
        "vehicle_type",
        "current_zip",
        "service_radius_miles",
        "rating",
        "completed_deliveries",
        "reviewed_at",
    )

    list_filter = (
        "approval_status",
        "is_active",
        "onboarding_completed",
        "address_verified",
        "contractor_agreement_accepted",
        "status",
        "vehicle_type",
        "created_at",
        "reviewed_at",
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
        "account_notes",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "contractor_agreement_accepted_at",
        "address_verified_at",
        "onboarding_completed_at",
        "reviewed_at",
        "reviewed_by",
        "deactivated_at",
        "driver_photo_preview",
        "vehicle_photo_preview",
        "driver_license_link",
        "insurance_link",
        "vehicle_registration_link",
    )

    actions = (
        approve_drivers,
        reject_drivers,
        activate_drivers,
        deactivate_drivers,
    )

    fieldsets = (
        (
            "Driver Account",
            {
                "fields": (
                    "user",
                    "approval_status",
                    "is_active",
                    "status",
                    "onboarding_completed",
                    "onboarding_completed_at",
                )
            },
        ),
        (
            "Application Review",
            {
                "fields": (
                    "reviewed_at",
                    "reviewed_by",
                    "deactivated_at",
                    "account_notes",
                )
            },
        ),
        (
            "Driver Verification Center",
            {
                "fields": (
                    "profile_photo",
                    "driver_photo_preview",
                    "vehicle_make",
                    "vehicle_model",
                    "vehicle_year",
                    "vehicle_color",
                    "license_plate",
                    "vehicle_photo",
                    "vehicle_photo_preview",
                    "driver_license_document",
                    "driver_license_link",
                    "insurance_document",
                    "insurance_link",
                    "vehicle_registration_document",
                    "vehicle_registration_link",
                    "documents_reviewed",
                    "documents_reviewed_at",
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
            "Working Area",
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

    @admin.display(
        boolean=True,
        description="Verification Complete",
    )
    def verification_complete(self, obj):
        return obj.verification_documents_complete

    @admin.display(description="Driver Photo Preview")
    def driver_photo_preview(self, obj):
        if not obj.profile_photo:
            return "No driver photo uploaded."

        return format_html(
            '<img src="{}" style="width:180px;max-height:220px;'
            'object-fit:cover;border-radius:12px;" alt="Driver photo">',
            obj.profile_photo.url,
        )

    @admin.display(description="Vehicle Photo Preview")
    def vehicle_photo_preview(self, obj):
        if not obj.vehicle_photo:
            return "No vehicle photo uploaded."

        return format_html(
            '<img src="{}" style="width:240px;max-height:180px;'
            'object-fit:cover;border-radius:12px;" alt="Vehicle photo">',
            obj.vehicle_photo.url,
        )

    @admin.display(description="Driver License")
    def driver_license_link(self, obj):
        if not obj.driver_license_document:
            return "Not uploaded."

        return format_html(
            '<a href="{}" target="_blank" rel="noopener">'
            'Open Driver License</a>',
            obj.driver_license_document.url,
        )

    @admin.display(description="Insurance")
    def insurance_link(self, obj):
        if not obj.insurance_document:
            return "Not uploaded."

        return format_html(
            '<a href="{}" target="_blank" rel="noopener">'
            'Open Insurance Document</a>',
            obj.insurance_document.url,
        )

    @admin.display(description="Vehicle Registration")
    def vehicle_registration_link(self, obj):
        if not obj.vehicle_registration_document:
            return "Not uploaded."

        return format_html(
            '<a href="{}" target="_blank" rel="noopener">'
            'Open Vehicle Registration</a>',
            obj.vehicle_registration_document.url,
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
        "partner__user__email",
        "pickup_zip",
        "delivery_zip",
    )

    readonly_fields = (
        "created_at",
        "accepted_at",
        "picked_up_at",
        "delivered_at",
    )
