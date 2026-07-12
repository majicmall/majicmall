from django.contrib import admin, messages
from django.utils import timezone
from django.utils.html import format_html

from .models import DeliveryJob, DeliveryPartner


@admin.action(description="Mark all verification items reviewed")
def mark_documents_reviewed(modeladmin, request, queryset):
    completed = 0
    skipped = 0
    now = timezone.now()

    for partner in queryset:
        if not partner.verification_documents_complete:
            skipped += 1
            continue

        partner.profile_photo_reviewed = True
        partner.vehicle_information_reviewed = True
        partner.vehicle_photo_reviewed = True
        partner.driver_license_reviewed = True
        partner.insurance_reviewed = True
        partner.vehicle_registration_reviewed = True
        partner.documents_reviewed = True
        partner.documents_reviewed_at = now
        partner.documents_reviewed_by = request.user

        partner.save(
            update_fields=[
                "profile_photo_reviewed",
                "vehicle_information_reviewed",
                "vehicle_photo_reviewed",
                "driver_license_reviewed",
                "insurance_reviewed",
                "vehicle_registration_reviewed",
                "documents_reviewed",
                "documents_reviewed_at",
                "documents_reviewed_by",
                "updated_at",
            ]
        )

        completed += 1

    if completed:
        modeladmin.message_user(
            request,
            (
                f"{completed} driver verification record(s) "
                "marked reviewed."
            ),
            level=messages.SUCCESS,
        )

    if skipped:
        modeladmin.message_user(
            request,
            (
                f"{skipped} driver record(s) were skipped because "
                "required uploads or vehicle details are missing."
            ),
            level=messages.WARNING,
        )


@admin.action(description="Request driver verification corrections")
def request_verification_corrections(
    modeladmin,
    request,
    queryset,
):
    updated = queryset.update(
        documents_reviewed=False,
        documents_reviewed_at=None,
        documents_reviewed_by=None,
        approval_status="pending",
        status="offline",
    )

    modeladmin.message_user(
        request,
        (
            f"{updated} driver application(s) returned to pending "
            "review. Add details in Verification Review Notes."
        ),
        level=messages.WARNING,
    )


@admin.action(description="Approve selected verified drivers")
def approve_drivers(modeladmin, request, queryset):
    approved = 0
    skipped = 0
    now = timezone.now()

    for partner in queryset:
        if not partner.verification_review_complete:
            skipped += 1
            continue

        partner.approval_status = "approved"
        partner.reviewed_at = now
        partner.reviewed_by = request.user
        partner.is_active = True
        partner.deactivated_at = None
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

        approved += 1

    if approved:
        modeladmin.message_user(
            request,
            (
                f"{approved} verified driver account(s) "
                "approved and activated."
            ),
            level=messages.SUCCESS,
        )

    if skipped:
        modeladmin.message_user(
            request,
            (
                f"{skipped} driver account(s) were not approved. "
                "Every required item must be uploaded and reviewed first."
            ),
            level=messages.ERROR,
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
    eligible = queryset.filter(
        approval_status="approved",
        documents_reviewed=True,
    )

    activated = 0
    skipped = 0

    for partner in queryset:
        if (
            partner not in eligible
            or not partner.verification_review_complete
        ):
            skipped += 1
            continue

        partner.is_active = True
        partner.deactivated_at = None
        partner.status = "offline"

        partner.save(
            update_fields=[
                "is_active",
                "deactivated_at",
                "status",
                "updated_at",
            ]
        )

        activated += 1

    if activated:
        modeladmin.message_user(
            request,
            f"{activated} approved driver account(s) activated.",
            level=messages.SUCCESS,
        )

    if skipped:
        modeladmin.message_user(
            request,
            (
                f"{skipped} account(s) were skipped because they "
                "are not fully approved and verified."
            ),
            level=messages.WARNING,
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
        "verification_submission_complete",
        "verification_review_complete_display",
        "is_active",
        "onboarding_completed",
        "status",
        "vehicle_type",
        "current_zip",
        "rating",
        "reviewed_at",
    )

    list_filter = (
        "approval_status",
        "documents_reviewed",
        "profile_photo_reviewed",
        "vehicle_information_reviewed",
        "vehicle_photo_reviewed",
        "driver_license_reviewed",
        "insurance_reviewed",
        "vehicle_registration_reviewed",
        "is_active",
        "onboarding_completed",
        "address_verified",
        "status",
        "vehicle_type",
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
        "vehicle_make",
        "vehicle_model",
        "license_plate",
        "account_notes",
        "verification_review_notes",
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
        "documents_reviewed_at",
        "documents_reviewed_by",
        "driver_photo_preview",
        "vehicle_photo_preview",
        "driver_license_link",
        "insurance_link",
        "vehicle_registration_link",
        "submission_progress_display",
        "review_progress_display",
    )

    actions = (
        mark_documents_reviewed,
        request_verification_corrections,
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
            "Administrative Review",
            {
                "fields": (
                    "submission_progress_display",
                    "review_progress_display",
                    "documents_reviewed",
                    "documents_reviewed_at",
                    "documents_reviewed_by",
                    "verification_review_notes",
                    "reviewed_at",
                    "reviewed_by",
                    "deactivated_at",
                    "account_notes",
                )
            },
        ),
        (
            "Driver Identity Review",
            {
                "fields": (
                    "profile_photo",
                    "driver_photo_preview",
                    "profile_photo_reviewed",
                )
            },
        ),
        (
            "Vehicle Review",
            {
                "fields": (
                    "vehicle_make",
                    "vehicle_model",
                    "vehicle_year",
                    "vehicle_color",
                    "license_plate",
                    "vehicle_information_reviewed",
                    "vehicle_photo",
                    "vehicle_photo_preview",
                    "vehicle_photo_reviewed",
                )
            },
        ),
        (
            "Required Documents",
            {
                "fields": (
                    "driver_license_document",
                    "driver_license_link",
                    "driver_license_reviewed",
                    "insurance_document",
                    "insurance_link",
                    "insurance_reviewed",
                    "vehicle_registration_document",
                    "vehicle_registration_link",
                    "vehicle_registration_reviewed",
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
        description="Submission Complete",
    )
    def verification_submission_complete(self, obj):
        return obj.verification_documents_complete

    @admin.display(
        boolean=True,
        description="Review Complete",
    )
    def verification_review_complete_display(self, obj):
        return obj.verification_review_complete

    @admin.display(description="Submission Progress")
    def submission_progress_display(self, obj):
        return format_html(
            "<strong>{}%</strong> — {} of {} required items submitted",
            obj.verification_percentage,
            obj.verification_completed_items,
            obj.verification_total_items,
        )

    @admin.display(description="Review Progress")
    def review_progress_display(self, obj):
        return format_html(
            "<strong>{}%</strong> — {} of {} required items reviewed",
            obj.verification_review_percentage,
            obj.verification_review_completed_items,
            obj.verification_review_total_items,
        )

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
            '<img src="{}" style="width:260px;max-height:190px;'
            'object-fit:cover;border-radius:12px;" alt="Vehicle photo">',
            obj.vehicle_photo.url,
        )

    @admin.display(description="Driver License")
    def driver_license_link(self, obj):
        if not obj.driver_license_document:
            return "Not uploaded."

        return format_html(
            '<a href="{}" target="_blank" rel="noopener">'
            "Open Driver License</a>",
            obj.driver_license_document.url,
        )

    @admin.display(description="Insurance")
    def insurance_link(self, obj):
        if not obj.insurance_document:
            return "Not uploaded."

        return format_html(
            '<a href="{}" target="_blank" rel="noopener">'
            "Open Insurance Document</a>",
            obj.insurance_document.url,
        )

    @admin.display(description="Vehicle Registration")
    def vehicle_registration_link(self, obj):
        if not obj.vehicle_registration_document:
            return "Not uploaded."

        return format_html(
            '<a href="{}" target="_blank" rel="noopener">'
            "Open Vehicle Registration</a>",
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
