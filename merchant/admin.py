from django.contrib import admin
from .models import MerchantStore, Product, Order, OrderItem

@admin.register(MerchantStore)
class MerchantStoreAdmin(admin.ModelAdmin):
    list_display = ("store_name", "owner", "plan", "created_at")
    search_fields = ("store_name", "owner__username", "owner__email")
    list_filter = ("plan", "created_at")
    readonly_fields = ("created_at",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "store", "price", "created_at")
    search_fields = ("name", "store__store_name")
    list_filter = ("store", "created_at")
    readonly_fields = ("created_at",)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ("product", "name", "quantity", "unit_price")
    autocomplete_fields = ("product",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "store", "status", "total", "created_at")
    list_filter = ("status", "store", "created_at")
    date_hierarchy = "created_at"
    search_fields = ("id", "note", "store__store_name", "user__username", "user__email")
    inlines = [OrderItemInline]
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)

    # speed up list view
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("store", "user")

    # quick admin actions
    actions = ["mark_paid", "mark_shipped", "mark_completed"]

    def mark_paid(self, request, queryset):
        updated = queryset.update(status="paid")
        self.message_user(request, f"{updated} order(s) marked Paid.")
    mark_paid.short_description = "Mark selected orders as Paid"

    def mark_shipped(self, request, queryset):
        updated = queryset.update(status="shipped")
        self.message_user(request, f"{updated} order(s) marked Shipped.")
    mark_shipped.short_description = "Mark selected orders as Shipped"

    def mark_completed(self, request, queryset):
        updated = queryset.update(status="completed")
        self.message_user(request, f"{updated} order(s) marked Completed.")
    mark_completed.short_description = "Mark selected orders as Completed"


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "name", "quantity", "unit_price")
    search_fields = ("name", "order__id", "order__store__store_name")
    list_select_related = ("order", "order__store")
