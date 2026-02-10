# merchant/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Auth
    path("login/",  auth_views.LoginView.as_view(template_name="merchant/login.html"), name="merchant-login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="merchant-login"), name="merchant-logout"),

    # Setup
    path("setup/", views.profile, name="merchant-setup"),

    # Merchant-facing pages
    path("dashboard/", views.dashboard, name="merchant-dashboard"),
    path("profile/",   views.profile,   name="merchant-profile"),
    path("reports/",   views.reports,   name="merchant-reports"),

    path("switch/<int:store_id>/", views.switch_store, name="merchant-switch-store"),


    # Orders
    path("orders/",                 views.order_list,   name="order-list"),
    path("orders/<int:order_id>/",  views.order_detail, name="order-detail"),

    # Reports export
    path("reports/export/", views.reports_export, name="merchant-reports-export"),

    # Product stubs
    path("products/add/",                     views.add_product,   name="add-product"),
    path("products/<int:product_id>/edit/",   views.edit_product,  name="edit-product"),
    path("products/<int:product_id>/delete/", views.delete_product, name="delete-product"),

    # Admin store management (staff)
    path("stores/",                             views.admin_store_list,    name="admin-store-list"),
    path("stores/<int:store_id>/archive/",      views.admin_store_archive, name="admin-store-archive"),
    path("stores/<int:store_id>/restore/",      views.admin_store_restore, name="admin-store-restore"),
    path("stores/<int:store_id>/purge/",        views.admin_store_purge,   name="admin-store-purge"),

    # Merchant self-service archive/restore
    path("store/archive/", views.merchant_store_archive, name="merchant-store-archive"),
    path("store/restore/", views.merchant_store_restore, name="merchant-store-restore"),

    # Payment settings
    path("payments/",                       views.payment_settings,     name="merchant-payment-settings"),
    path("payments/add/",                   views.payment_method_create, name="merchant-payment-create"),
    path("payments/<int:method_id>/edit/",  views.payment_method_edit,  name="merchant-payment-edit"),
    path("payments/<int:method_id>/delete/",views.payment_method_delete, name="merchant-payment-delete"),

    # Demo checkout
    path("checkout/start/",   views.checkout_start,   name="merchant-checkout-start"),
    path("checkout/success/", views.checkout_success, name="merchant-checkout-success"),
    path("checkout/cancel/",  views.checkout_cancel,  name="merchant-checkout-cancel"),

    # Plans (pricing & checkout)
    path("plans/",                               views.plan_pricing,          name="merchant-plans"),
    path("plans/<str:plan_slug>/checkout/",      views.plan_checkout,         name="merchant-plan-checkout"),
    path("plans/success/",                       views.plan_checkout_success, name="merchant-plan-success"),
    path("plans/cancel/",                        views.plan_checkout_cancel,  name="merchant-plan-cancel"),

    # Admin payment methods
    path("admin/payments/", views.admin_payment_methods, name="admin-payment-methods"),

    # Webhooks
    path("webhooks/stripe/", views.webhook_stripe, name="merchant-webhook-stripe"),
    path("webhooks/paypal/", views.webhook_paypal, name="merchant-webhook-paypal"),
]
