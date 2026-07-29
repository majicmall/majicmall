from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db.models import Count, Sum
from django.utils.html import format_html

from .models import (
    CitizenLevelReward,
    CoinTransaction,
    MajesticCoinSettings,
    MajestianRecommendation,
    MajestianWallet,
)
from .services import EconomyEngine


@admin.register(MajesticCoinSettings)
class MajesticCoinSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        (
            "Majestic Coin Identity",
            {
                "fields": (
                    "coin_name",
                    "coin_symbol",
                    "currency_code",
                    "coin_value",
                    "is_active",
                )
            },
        ),
        (
            "Redemption Policy",
            {
                "fields": (
                    "minimum_redemption_coins",
                    "maximum_daily_redemption_coins",
                    "redemption_enabled",
                )
            },
        ),
        (
            "Reward Programs",
            {
                "fields": (
                    "referral_rewards_enabled",
                    "merchant_rewards_enabled",
                    "creator_rewards_enabled",
                    "purchase_rewards_enabled",
                    "bonus_events_enabled",
                )
            },
        ),
        (
            "Reward Protection",
            {
                "fields": (
                    "require_payment_confirmation",
                    "reward_hold_days",
                )
            },
        ),
        (
            "Audit",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    readonly_fields = ("created_at", "updated_at")

    def has_add_permission(self, request):
        return not MajesticCoinSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CitizenLevelReward)
class CitizenLevelRewardAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "referral_percentage_display",
        "display_order",
        "is_active",
        "updated_at",
    )
    list_editable = (
        "display_order",
        "is_active",
    )
    list_filter = ("is_active",)
    search_fields = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("display_order", "name")

    @admin.display(description="Referral reward", ordering="referral_percentage")
    def referral_percentage_display(self, obj):
        return f"{obj.referral_percentage}%"


@admin.register(MajestianWallet)
class MajestianWalletAdmin(admin.ModelAdmin):
    list_display = (
        "wallet_owner",
        "status",
        "available_balance",
        "pending_balance",
        "platform_value_display",
        "lifetime_earned_coins",
        "opportunity_score",
        "last_transaction_at",
    )
    list_filter = ("status", "created_at", "last_transaction_at")
    search_fields = (
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
    )
    readonly_fields = (
        "user",
        "available_coins",
        "pending_coins",
        "lifetime_earned_coins",
        "lifetime_redeemed_coins",
        "lifetime_reversed_coins",
        "lifetime_expired_coins",
        "last_transaction_at",
        "created_at",
        "updated_at",
        "platform_value_detail",
    )

    fieldsets = (
        (
            "Majestian",
            {
                "fields": (
                    "user",
                    "status",
                    "opportunity_score",
                )
            },
        ),
        (
            "Current Balances",
            {
                "fields": (
                    "available_coins",
                    "pending_coins",
                    "platform_value_detail",
                )
            },
        ),
        (
            "Lifetime Activity",
            {
                "fields": (
                    "lifetime_earned_coins",
                    "lifetime_redeemed_coins",
                    "lifetime_reversed_coins",
                    "lifetime_expired_coins",
                )
            },
        ),
        (
            "Audit",
            {
                "fields": (
                    "last_transaction_at",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    actions = None

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Majestian", ordering="user__first_name")
    def wallet_owner(self, obj):
        full_name = obj.user.get_full_name().strip()
        return full_name or obj.user.get_username()

    @admin.display(description="Available MC", ordering="available_coins")
    def available_balance(self, obj):
        return f"{obj.available_coins:,.2f} MC"

    @admin.display(description="Pending MC", ordering="pending_coins")
    def pending_balance(self, obj):
        return f"{obj.pending_coins:,.2f} MC"

    @admin.display(description="Platform value")
    def platform_value_display(self, obj):
        return f"${obj.available_platform_value:,.2f}"

    @admin.display(description="Current platform value")
    def platform_value_detail(self, obj):
        return format_html(
            "<strong>{}</strong> available + "
            "<strong>{}</strong> pending",
            f"${obj.available_platform_value:,.2f}",
            f"${obj.pending_platform_value:,.2f}",
        )


@admin.register(CoinTransaction)
class CoinTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "short_public_id",
        "wallet_owner",
        "transaction_type",
        "direction",
        "status",
        "coin_amount_display",
        "platform_value_display",
        "created_at",
    )
    list_filter = (
        "status",
        "direction",
        "transaction_type",
        "created_at",
    )
    search_fields = (
        "public_id",
        "wallet__user__username",
        "wallet__user__email",
        "wallet__user__first_name",
        "wallet__user__last_name",
        "description",
        "reference_id",
        "idempotency_key",
    )
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    actions = (
        "post_selected_pending_rewards",
    )

    readonly_fields = (
        "public_id",
        "wallet",
        "transaction_type",
        "direction",
        "status",
        "coin_amount",
        "coin_value_snapshot",
        "platform_value",
        "description",
        "reference_type",
        "reference_id",
        "idempotency_key",
        "metadata",
        "available_at",
        "posted_at",
        "reversed_at",
        "reversal_of",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            "Transaction",
            {
                "fields": (
                    "public_id",
                    "wallet",
                    "transaction_type",
                    "direction",
                    "status",
                    "description",
                )
            },
        ),
        (
            "Value",
            {
                "fields": (
                    "coin_amount",
                    "coin_value_snapshot",
                    "platform_value",
                )
            },
        ),
        (
            "Reference",
            {
                "fields": (
                    "reference_type",
                    "reference_id",
                    "idempotency_key",
                    "reversal_of",
                )
            },
        ),
        (
            "Timing",
            {
                "fields": (
                    "available_at",
                    "posted_at",
                    "reversed_at",
                    "created_at",
                    "updated_at",
                )
            },
        ),
        (
            "Metadata",
            {
                "fields": ("metadata",),
                "classes": ("collapse",),
            },
        ),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.method in ("GET", "HEAD", "OPTIONS")

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="ID")
    def short_public_id(self, obj):
        return str(obj.public_id)[:8]

    @admin.display(description="Majestian")
    def wallet_owner(self, obj):
        full_name = obj.wallet.user.get_full_name().strip()
        return full_name or obj.wallet.user.get_username()

    @admin.display(description="Coins", ordering="coin_amount")
    def coin_amount_display(self, obj):
        sign = "+" if obj.direction == obj.Direction.CREDIT else "-"
        return f"{sign}{obj.coin_amount:,.2f} MC"

    @admin.display(description="Value", ordering="platform_value")
    def platform_value_display(self, obj):
        return f"${obj.platform_value:,.2f}"

    @admin.action(description="Post selected eligible pending rewards")
    def post_selected_pending_rewards(self, request, queryset):
        posted = 0
        skipped = 0

        for entry in queryset.filter(status=CoinTransaction.Status.PENDING):
            try:
                EconomyEngine.post_pending_transaction(entry)
                posted += 1
            except ValidationError:
                skipped += 1

        if posted:
            self.message_user(
                request,
                f"{posted} pending reward(s) posted.",
                level=messages.SUCCESS,
            )

        if skipped:
            self.message_user(
                request,
                f"{skipped} reward(s) were not yet eligible.",
                level=messages.WARNING,
            )

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        totals = CoinTransaction.objects.filter(
            status=CoinTransaction.Status.POSTED,
            direction=CoinTransaction.Direction.CREDIT,
        ).aggregate(
            total_coins=Sum("coin_amount"),
            total_value=Sum("platform_value"),
        )

        extra_context["economy_total_coins"] = (
            totals["total_coins"] or 0
        )
        extra_context["economy_total_value"] = (
            totals["total_value"] or 0
        )

        return super().changelist_view(
            request,
            extra_context=extra_context,
        )


@admin.register(MajestianRecommendation)
class MajestianRecommendationAdmin(admin.ModelAdmin):
    list_display = (
        "short_public_id",
        "referrer_name",
        "referred_name",
        "recommendation_type",
        "citizen_level",
        "membership_amount_display",
        "reward_percentage_display",
        "coins_awarded_display",
        "status",
        "created_at",
    )
    list_filter = (
        "status",
        "recommendation_type",
        "citizen_level",
        "fraud_review_required",
        "created_at",
    )
    search_fields = (
        "public_id",
        "referrer__username",
        "referrer__email",
        "referrer__first_name",
        "referrer__last_name",
        "referred_user__username",
        "referred_user__email",
        "membership_name",
        "payment_reference",
        "referral_code",
    )
    autocomplete_fields = (
        "referrer",
        "referred_user",
        "citizen_level",
    )
    readonly_fields = (
        "public_id",
        "reward_percentage_snapshot",
        "reward_value",
        "coins_awarded",
        "reward_transaction",
        "rewarded_at",
        "created_at",
        "updated_at",
    )
    actions = (
        "issue_selected_recommendation_rewards",
    )

    fieldsets = (
        (
            "Recommendation",
            {
                "fields": (
                    "public_id",
                    "referrer",
                    "referred_user",
                    "recommendation_type",
                    "citizen_level",
                    "referral_code",
                )
            },
        ),
        (
            "Membership and Payment",
            {
                "fields": (
                    "membership_name",
                    "membership_amount",
                    "payment_reference",
                    "payment_confirmed_at",
                )
            },
        ),
        (
            "Reward",
            {
                "fields": (
                    "reward_percentage_snapshot",
                    "reward_value",
                    "coins_awarded",
                    "reward_transaction",
                    "rewarded_at",
                )
            },
        ),
        (
            "Review",
            {
                "fields": (
                    "status",
                    "fraud_review_required",
                    "fraud_review_notes",
                    "administrator_notes",
                )
            },
        ),
        (
            "Metadata",
            {
                "fields": (
                    "metadata",
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(description="ID")
    def short_public_id(self, obj):
        return str(obj.public_id)[:8]

    @admin.display(description="Referrer")
    def referrer_name(self, obj):
        name = obj.referrer.get_full_name().strip()
        return name or obj.referrer.get_username()

    @admin.display(description="New Majestian")
    def referred_name(self, obj):
        if not obj.referred_user:
            return "Not connected"

        name = obj.referred_user.get_full_name().strip()
        return name or obj.referred_user.get_username()

    @admin.display(description="Membership")
    def membership_amount_display(self, obj):
        return f"${obj.membership_amount:,.2f}"

    @admin.display(description="Reward %")
    def reward_percentage_display(self, obj):
        return f"{obj.reward_percentage_snapshot}%"

    @admin.display(description="Coins")
    def coins_awarded_display(self, obj):
        return f"{obj.coins_awarded:,.2f} MC"

    @admin.action(description="Issue rewards for selected recommendations")
    def issue_selected_recommendation_rewards(self, request, queryset):
        rewarded = 0
        skipped = 0

        for recommendation in queryset:
            try:
                EconomyEngine.award_recommendation(recommendation)
                rewarded += 1
            except ValidationError:
                skipped += 1

        if rewarded:
            self.message_user(
                request,
                f"{rewarded} recommendation reward(s) created.",
                level=messages.SUCCESS,
            )

        if skipped:
            self.message_user(
                request,
                f"{skipped} recommendation(s) could not be rewarded.",
                level=messages.WARNING,
            )
