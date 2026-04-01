from django.urls import path
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    # =========================
    # Auth (redirect to allauth)
    # =========================
    path("login/", RedirectView.as_view(url="/accounts/login/", permanent=False), name="merchant-login"),
    path("logout/", RedirectView.as_view(url="/accounts/logout/", permanent=False), name="merchant-logout"),

    # =========================
    # Setup / Profile
    # =========================
    path("setup/", views.profile, name="merchant-setup"),
    path("profile/", views.profile, name="merchant-profile"),
    path("switch/<int:store_id>/", views.switch_store, name="merchant-switch-store"),

    # =========================
    # Dashboard / Reports
    # =========================
    path("dashboard/", views.dashboard, name="merchant-dashboard"),
    path("reports/", views.reports, name="merchant-reports"),
    path("reports/export/", views.reports_export, name="merchant-reports-export"),

    # =========================
    # Categories
    # =========================
    path("categories/", views.category_list, name="merchant-category-list"),
    path("categories/add/", views.add_category, name="merchant-add-category"),

    # =========================
    # Products
    # =========================
    path("products/add/", views.add_product, name="merchant-add-product"),
    path("products/<int:product_id>/edit/", views.edit_product, name="merchant-edit-product"),
    path("products/<int:product_id>/delete/", views.delete_product, name="merchant-delete-product"),

    # =========================
    # Orders
    # =========================
    path("orders/", views.order_list, name="order-list"),
    path("orders/<int:order_id>/", views.order_detail, name="order-detail"),
    path("orders/<int:order_id>/status/", views.order_update_status, name="order-update-status"),

    # =========================
    # Cart (Public)
    # =========================
    path("cart/", views.cart_view, name="cart-view"),
    path("cart/add/<int:product_id>/", views.cart_add, name="cart-add"),
    path("cart/remove/<int:product_id>/", views.cart_remove, name="cart-remove"),

    # =========================
    # Public Checkout (Customer)
    # =========================
    path("checkout/", views.public_checkout, name="public-checkout"),
    path("checkout/apply-promo/", views.public_checkout_apply_promo, name="public-checkout-apply-promo"),
    path("checkout/submit/", views.public_checkout_submit, name="public-checkout-submit"),
    path("checkout/success/", views.public_checkout_success, name="public-checkout-success"),
    path("checkout/cancel/", views.public_checkout_cancel, name="public-checkout-cancel"),

    # =========================
    # Merchant Payment Settings
    # =========================
    path("payments/", views.payment_settings, name="merchant-payment-settings"),
    path("payments/add/", views.payment_method_create, name="merchant-payment-create"),
    path("payments/<int:method_id>/edit/", views.payment_method_edit, name="merchant-payment-edit"),
    path("payments/<int:method_id>/delete/", views.payment_method_delete, name="merchant-payment-delete"),

    # =========================
    # Merchant Demo Checkout (internal)
    # =========================
    path("checkout/start/", views.checkout_start, name="merchant-checkout-start"),
    path("checkout/success-demo/", views.checkout_success, name="merchant-checkout-success"),
    path("checkout/cancel-demo/", views.checkout_cancel, name="merchant-checkout-cancel"),

    # =========================
    # Plans
    # =========================
    path("plans/", views.plan_pricing, name="merchant-plans"),
    path("plans/<str:plan_slug>/checkout/", views.plan_checkout, name="merchant-plan-checkout"),
    path("plans/success/", views.plan_checkout_success, name="merchant-plan-success"),
    path("plans/cancel/", views.plan_checkout_cancel, name="merchant-plan-cancel"),

    # =========================
    # Admin Store Management
    # =========================
    path("stores/", views.admin_store_list, name="admin-store-list"),
    path("stores/<int:store_id>/archive/", views.admin_store_archive, name="admin-store-archive"),
    path("stores/<int:store_id>/restore/", views.admin_store_restore, name="admin-store-restore"),
    path("stores/<int:store_id>/purge/", views.admin_store_purge, name="admin-store-purge"),

    # =========================
    # Merchant Self-Service Store
    # =========================
    path("store/archive/", views.merchant_store_archive, name="merchant-store-archive"),
    path("store/restore/", views.merchant_store_restore, name="merchant-store-restore"),

    # =========================
    # Admin Payment Methods
    # =========================
    path("admin/payments/", views.admin_payment_methods, name="admin-payment-methods"),

    # =========================
    # Webhooks
    # =========================
    path("webhooks/stripe/", views.webhook_stripe, name="merchant-webhook-stripe"),
    path("webhooks/paypal/", views.webhook_paypal, name="merchant-webhook-paypal"),
]