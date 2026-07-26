from django.contrib import admin
from django.utils import timezone

from .models import AdvertisingCreative, Campaign


class AdvertisingCreativeInline(admin.TabularInline):
    model = AdvertisingCreative
    extra = 0

    fields = (
        "title",
        "media_type",
        "approval_status",
        "is_enabled",
        "priority",
        "impressions",
        "clicks",
    )

    readonly_fields = (
        "impressions",
        "clicks",
    )

    show_change_link = True


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "advertiser_name",
        "status",
        "start_at",
        "end_at",
        "creative_count",
        "created_at",
    )

    list_filter = (
        "status",
        "start_at",
        "end_at",
        "created_at",
    )

    search_fields = (
        "name",
        "advertiser_name",
        "description",
        "internal_notes",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    date_hierarchy = "created_at"

    fieldsets = (
        (
            "Campaign",
            {
                "fields": (
                    "name",
                    "advertiser_name",
                    "description",
                    "status",
                    "budget",
                )
            },
        ),
        (
            "Schedule",
            {
                "fields": (
                    "start_at",
                    "end_at",
                )
            },
        ),
        (
            "Internal Management",
            {
                "fields": (
                    "internal_notes",
                    "created_by",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    inlines = (AdvertisingCreativeInline,)

    def creative_count(self, obj):
        return obj.creatives.count()

    creative_count.short_description = "Creatives"

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user

        super().save_model(request, obj, form, change)


@admin.register(AdvertisingCreative)
class AdvertisingCreativeAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "campaign",
        "media_type",
        "approval_status",
        "is_enabled",
        "priority",
        "impressions",
        "clicks",
        "created_at",
    )

    list_filter = (
        "media_type",
        "approval_status",
        "is_enabled",
        "campaign__status",
        "created_at",
    )

    search_fields = (
        "title",
        "headline",
        "campaign__name",
        "campaign__advertiser_name",
        "destination_url",
    )

    readonly_fields = (
        "impressions",
        "clicks",
        "created_at",
        "updated_at",
        "reviewed_at",
    )

    autocomplete_fields = (
        "campaign",
        "created_by",
        "reviewed_by",
    )

    actions = (
        "approve_selected",
        "reject_selected",
        "enable_selected",
        "disable_selected",
    )

    fieldsets = (
        (
            "Creative",
            {
                "fields": (
                    "campaign",
                    "title",
                    "media_type",
                    "file",
                    "external_media_url",
                )
            },
        ),
        (
            "Advertisement Message",
            {
                "fields": (
                    "headline",
                    "call_to_action",
                    "destination_url",
                    "alt_text",
                )
            },
        ),
        (
            "Targeting and Placement",
            {
                "fields": (
                    "target_zones",
                    "placement_codes",
                    "priority",
                    "play_frequency",
                    "duration_seconds",
                )
            },
        ),
        (
            "Schedule",
            {
                "fields": (
                    "start_at",
                    "end_at",
                    "is_enabled",
                )
            },
        ),
        (
            "Review",
            {
                "fields": (
                    "approval_status",
                    "review_notes",
                    "reviewed_by",
                    "reviewed_at",
                )
            },
        ),
        (
            "Analytics",
            {
                "fields": (
                    "impressions",
                    "clicks",
                )
            },
        ),
        (
            "System",
            {
                "fields": (
                    "created_by",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user

        if (
            "approval_status" in form.changed_data
            and obj.approval_status
            in {
                AdvertisingCreative.ApprovalStatus.APPROVED,
                AdvertisingCreative.ApprovalStatus.REJECTED,
            }
        ):
            obj.reviewed_by = request.user
            obj.reviewed_at = timezone.now()

        super().save_model(request, obj, form, change)

    @admin.action(description="Approve selected creatives")
    def approve_selected(self, request, queryset):
        queryset.update(
            approval_status=AdvertisingCreative.ApprovalStatus.APPROVED,
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
        )

    @admin.action(description="Reject selected creatives")
    def reject_selected(self, request, queryset):
        queryset.update(
            approval_status=AdvertisingCreative.ApprovalStatus.REJECTED,
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
        )

    @admin.action(description="Enable selected creatives")
    def enable_selected(self, request, queryset):
        queryset.update(is_enabled=True)

    @admin.action(description="Disable selected creatives")
    def disable_selected(self, request, queryset):
        queryset.update(is_enabled=False)
