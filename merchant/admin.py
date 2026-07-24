from django.contrib import admin
from .models import (
    MallZone,
    MerchantStore,
    StoreCategory,
    Product,
    Order,
    OrderItem,
    MerchantPaymentMethod,
)


@admin.register(MallZone)
class MallZoneAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "sort_order")
    list_editable = ("is_active", "sort_order")
    search_fields = ("name",)
    ordering = ("sort_order", "name")


@admin.register(MerchantStore)
class MerchantStoreAdmin(admin.ModelAdmin):
    list_display = (
        "store_name",
        "owner",
        "contact_person",
        "contact_email",
        "contact_phone",
        "zone",
        "plan",
        "is_featured",
        "featured_slot",
        "is_public",
        "is_archived",
    )
    list_filter = (
        "zone",
        "plan",
        "is_featured",
        "is_public",
        "is_archived",
    )
    search_fields = (
        "store_name",
        "owner__username",
        "owner__email",
        "contact_person",
        "contact_email",
        "contact_phone",
    )
    list_editable = (
        "is_featured",
        "featured_slot",
        "is_public",
        "is_archived",
    )
    fieldsets = (
        ("Store Basics", {
            "fields": (
                "owner",
                "store_name",
                "slug",
                "logo",
                "storefront_image",
                "slogan",
                "description",
                "category",
                "zone",
                "plan",
            )
        }),
        ("Vendor Contact", {
            "fields": (
                "contact_person",
                "contact_email",
                "contact_phone",
            )
        }),
        ("Visibility & Featured Placement", {
            "fields": (
                "is_public",
                "is_archived",
                "is_featured",
                "featured_slot",
            )
        }),
        ("Admin Notes", {
            "fields": ("admin_notes",)
        }),
    )


@admin.register(StoreCategory)
class StoreCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "store", "slug")
    list_filter = ("store",)
    search_fields = ("name", "store__store_name")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "store", "category", "product_type", "price", "created_at")
    list_filter = ("product_type", "store", "category")
    search_fields = ("name", "store__store_name")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "store", "status", "total", "created_at")
    list_filter = ("status", "store")
    search_fields = ("id", "store__store_name")


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "name", "quantity", "unit_price")
    search_fields = ("name",)


@admin.register(MerchantPaymentMethod)
class MerchantPaymentMethodAdmin(admin.ModelAdmin):
    list_display = ("store", "provider", "display_name", "mode", "is_active", "is_default")
    list_filter = ("provider", "mode", "is_active", "is_default")
    search_fields = ("store__store_name", "display_name")


try:
    from .models import MerchantFulfillmentSettings

    @admin.register(MerchantFulfillmentSettings)
    class MerchantFulfillmentSettingsAdmin(admin.ModelAdmin):
        list_display = (
            "store",
            "availability_status",
            "merchant_type",
            "sound_alerts_enabled",
            "browser_notifications_enabled",
            "email_alerts_enabled",
            "default_preparation_minutes",
            "last_status_change_at",
        )

        list_filter = (
            "availability_status",
            "merchant_type",
            "sound_alerts_enabled",
            "browser_notifications_enabled",
            "email_alerts_enabled",
        )

        search_fields = (
            "store__store_name",
            "store__owner__username",
            "store__owner__email",
        )

except admin.sites.AlreadyRegistered:
    pass


# ============================================================
# MajicMall Megaverse Membership Administration
# ============================================================

from .models import (
    MajesticCoinTransaction,
    MajesticCoinWallet,
    MerchantMembership,
    MerchantMembershipHistory,
)


@admin.register(MerchantMembership)
class MerchantMembershipAdmin(admin.ModelAdmin):
    list_display = (
        "owner",
        "current_plan",
        "status",
        "member_since",
        "anniversary_date",
        "next_billing_date",
        "foundation_expires_on",
        "majestic_coins_awarded",
    )

    list_filter = (
        "current_plan",
        "status",
        "is_foundation_member",
        "foundation_pass_verified",
        "majestic_coins_awarded",
    )

    search_fields = (
        "owner__username",
        "owner__email",
        "foundation_member_number",
        "primary_store__store_name",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "majestic_coins_awarded_at",
    )


@admin.register(MerchantMembershipHistory)
class MerchantMembershipHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "membership",
        "change_type",
        "previous_plan",
        "new_plan",
        "previous_status",
        "new_status",
        "effective_date",
    )

    list_filter = (
        "change_type",
        "new_plan",
        "new_status",
        "effective_date",
    )

    search_fields = (
        "membership__owner__username",
        "membership__owner__email",
        "note",
    )

    readonly_fields = (
        "membership",
        "change_type",
        "previous_plan",
        "new_plan",
        "previous_status",
        "new_status",
        "effective_date",
        "note",
        "created_at",
    )


@admin.register(MajesticCoinWallet)
class MajesticCoinWalletAdmin(admin.ModelAdmin):
    list_display = (
        "owner",
        "balance",
        "updated_at",
    )

    search_fields = (
        "owner__username",
        "owner__email",
    )


@admin.register(MajesticCoinTransaction)
class MajesticCoinTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "wallet",
        "amount",
        "transaction_type",
        "reason",
        "balance_after",
        "created_at",
    )

    list_filter = (
        "transaction_type",
        "created_at",
    )

    search_fields = (
        "wallet__owner__username",
        "wallet__owner__email",
        "reason",
        "reference",
    )

    readonly_fields = (
        "wallet",
        "amount",
        "transaction_type",
        "reason",
        "reference",
        "balance_after",
        "created_at",
    )

