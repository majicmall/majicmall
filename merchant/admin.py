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
