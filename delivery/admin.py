from django.contrib import admin, messages
from django.utils import timezone

from .models import DeliveryPartner


def model_has_field(model, field_name):
    return any(field.name == field_name for field in model._meta.get_fields())


def first_existing_field(model, field_names):
    for field_name in field_names:
        if model_has_field(model, field_name):
            return field_name
    return None


@admin.action(description="Approve selected transport partners")
def approve_transport_partners(modeladmin, request, queryset):
    updated = 0

    for partner in queryset:
        changed_fields = []

        boolean_approval_field = first_existing_field(
            DeliveryPartner,
            [
                "is_approved",
                "approved",
                "application_approved",
                "documents_approved",
            ],
        )

        approval_status_field = first_existing_field(
            DeliveryPartner,
            [
                "approval_status",
                "application_status",
                "onboarding_status",
                "account_status",
            ],
        )

        reviewed_at_field = first_existing_field(
            DeliveryPartner,
            [
                "documents_reviewed_at",
                "reviewed_at",
                "approved_at",
            ],
        )

        reviewed_by_field = first_existing_field(
            DeliveryPartner,
            [
                "documents_reviewed_by",
                "reviewed_by",
                "approved_by",
            ],
        )

        active_field = first_existing_field(
            DeliveryPartner,
            [
                "is_active",
                "account_active",
                "active",
            ],
        )

        if boolean_approval_field:
            setattr(partner, boolean_approval_field, True)
            changed_fields.append(boolean_approval_field)

        if approval_status_field:
            field = DeliveryPartner._meta.get_field(approval_status_field)
            choice_values = [str(value).lower() for value, _label in field.choices]

            if "approved" in choice_values:
                setattr(partner, approval_status_field, "approved")
                changed_fields.append(approval_status_field)

        if reviewed_at_field:
            setattr(partner, reviewed_at_field, timezone.now())
            changed_fields.append(reviewed_at_field)

        if reviewed_by_field:
            setattr(partner, reviewed_by_field, request.user)
            changed_fields.append(reviewed_by_field)

        if active_field:
            setattr(partner, active_field, True)
            changed_fields.append(active_field)

        if changed_fields:
            partner.save(update_fields=list(dict.fromkeys(changed_fields)))
            updated += 1

    if updated:
        messages.success(
            request,
            f"{updated} transport partner application(s) approved.",
        )
    else:
        messages.warning(
            request,
            "No recognized approval fields were found on DeliveryPartner.",
        )


@admin.action(description="Activate selected transport partners")
def activate_transport_partners(modeladmin, request, queryset):
    active_field = first_existing_field(
        DeliveryPartner,
        ["is_active", "account_active", "active"],
    )

    if not active_field:
        messages.warning(
            request,
            "No recognized active-account field was found.",
        )
        return

    updated = queryset.update(**{active_field: True})
    messages.success(request, f"{updated} transport partner(s) activated.")


@admin.action(description="Deactivate selected transport partners")
def deactivate_transport_partners(modeladmin, request, queryset):
    active_field = first_existing_field(
        DeliveryPartner,
        ["is_active", "account_active", "active"],
    )

    if not active_field:
        messages.warning(
            request,
            "No recognized active-account field was found.",
        )
        return

    updated = queryset.update(**{active_field: False})
    messages.success(request, f"{updated} transport partner(s) deactivated.")


@admin.register(DeliveryPartner)
class DeliveryPartnerAdmin(admin.ModelAdmin):
    actions = [
        approve_transport_partners,
        activate_transport_partners,
        deactivate_transport_partners,
    ]

    list_per_page = 50
    list_select_related = True
    search_fields = ["user__username", "user__email", "phone"]

    def get_list_display(self, request):
        available = {
            field.name
            for field in DeliveryPartner._meta.get_fields()
        }

        preferred = [
            "id",
            "user",
            "phone",
            "home_zip",
            "current_zip",
            "vehicle_type",
            "approval_status",
            "application_status",
            "is_approved",
            "is_active",
            "status",
        ]

        return tuple(field for field in preferred if field in available)

    def get_list_filter(self, request):
        available = {
            field.name
            for field in DeliveryPartner._meta.get_fields()
        }

        preferred = [
            "approval_status",
            "application_status",
            "is_approved",
            "is_active",
            "status",
            "vehicle_type",
        ]

        return tuple(field for field in preferred if field in available)

    def get_readonly_fields(self, request, obj=None):
        available = {
            field.name
            for field in DeliveryPartner._meta.get_fields()
        }

        preferred = [
            "documents_reviewed_at",
            "reviewed_at",
            "approved_at",
        ]

        return tuple(field for field in preferred if field in available)
