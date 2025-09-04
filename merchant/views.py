# merchant/views.py
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal, InvalidOperation
import csv
import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum
from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

# ----- Models ------------------------------------------------------------------
from .models import MerchantStore, Product, Order, OrderItem, MerchantPaymentMethod

# ----- Forms -------------------------------------------------------------------
from .forms import StoreForm, MerchantPaymentMethodForm

# ----- Payments adapters -------------------------------------------------------
from .payments.adapters import build_adapter

Store = MerchantStore  # alias to keep older references working


# ===== Helpers =================================================================
def staff_required(view_func):
    """Require logged-in staff/superuser."""
    return login_required(
        user_passes_test(lambda u: u.is_staff or u.is_superuser)(view_func)
    )


def _get_user_store_or_none(request):
    """Best effort to fetch the current user's store."""
    try:
        return Store.objects.select_related("owner").get(owner=request.user)
    except Store.DoesNotExist:
        return None


def _redirect_if_archived(request, store: Store | None):
    """
    If you call this at the top of a view that requires an active store,
    it redirects archived stores to the profile page with a message.
    """
    if store and getattr(store, "is_archived", False):
        messages.warning(
            request,
            "This store is archived. Some actions are disabled until it is restored.",
        )
        return redirect("merchant-profile")
    return None


# ===== Merchant dashboard / profile / reports ==================================
@login_required
def dashboard(request):
    """
    Merchant dashboard: shows store summary, products, recent orders.
    Template: merchant/dashboard.html
    """
    store = _get_user_store_or_none(request)
    if not store:
        messages.info(request, "Create your store to continue.")
        return redirect("merchant-profile")

    guard = _redirect_if_archived(request, store)
    if guard:
        return guard

    products_qs = store.products.all()
    orders_qs = store.orders.all().order_by("-created_at")

    product_count = products_qs.count()
    order_count = orders_qs.count()
    revenue = orders_qs.aggregate(total=Sum("total"))["total"] or Decimal("0.00")

    # Recent orders (limit 10)
    recent_orders = list(orders_qs[:10])

    # Simple placeholders for inline spark-lines (replace with real series if you have them)
    order_spark = ",".join(str(i) for i in range(1, 17))
    product_spark = ",".join(str(i * 2) for i in range(1, 17))
    revenue_spark = ",".join(str(i * 5) for i in range(1, 17))

    context = {
        "merchant": getattr(request.user, "merchant", None),
        "store": store,
        "products": products_qs,
        "product_count": product_count,
        "order_count": order_count,
        "revenue": revenue,
        "recent_orders": recent_orders,
        "order_spark": order_spark,
        "product_spark": product_spark,
        "revenue_spark": revenue_spark,
        "page_obj": None,
        "q": "",
    }
    return render(request, "merchant/dashboard.html", context)


@login_required
def profile(request):
    """
    Store Profile: shows and edits the merchant's store info.
    Binds a ModelForm to the current user's store instance (and creates one if missing).
    """
    store = _get_user_store_or_none(request)

    # If the user somehow has no store yet, create a blank one so the form binds
    if not store:
        store = MerchantStore.objects.create(
            owner=request.user,
            store_name="",
            category="",
            plan="starter",
        )

    if request.method == "POST":
        form = StoreForm(request.POST, request.FILES, instance=store)
        if form.is_valid():
            form.save()
            messages.success(request, "Store profile saved.")
            return redirect("merchant-profile")
    else:
        form = StoreForm(instance=store)

    return render(request, "merchant/profile.html", {"store": store, "form": form})


@login_required
def reports(request):
    """
    Reports & Analytics page (lite vs Chart.js via ?charts=pro).
    Template: merchant/reports.html
    """
    store = _get_user_store_or_none(request)
    if not store:
        messages.info(request, "Create your store to view reports.")
        return redirect("merchant-profile")

    guard = _redirect_if_archived(request, store)
    if guard:
        return guard

    use_chartjs = request.GET.get("charts") == "pro"
    try:
        days = int(request.GET.get("range", "7"))
    except ValueError:
        days = 7
    days = days if days in (7, 30, 90) else 7

    since = timezone.now() - timedelta(days=days)
    orders_qs = store.orders.filter(created_at__gte=since).order_by("created_at")
    total_orders = orders_qs.count()
    total_revenue = orders_qs.aggregate(total=Sum("total"))["total"] or Decimal("0.00")
    product_count = store.products.count()

    labels: list[str] = []
    orders_series: list[int] = []
    revenue_series: list[float] = []

    # Pre-aggregate in Python (ok for small datasets; DB annotate for larger sets)
    bucket: dict[str, dict[str, Decimal | int]] = {}
    for o in orders_qs:
        key = o.created_at.astimezone(timezone.get_current_timezone()).date().isoformat()
        if key not in bucket:
            bucket[key] = {"orders": 0, "revenue": Decimal("0.00")}
        bucket[key]["orders"] += 1
        bucket[key]["revenue"] += o.total or Decimal("0.00")

    tz = timezone.get_current_timezone()
    for i in range(days):
        d = (timezone.now().astimezone(tz) - timedelta(days=days - 1 - i)).date()
        key = d.isoformat()
        labels.append(d.strftime("%b %d"))
        orders_series.append(int(bucket.get(key, {}).get("orders", 0)))
        revenue_series.append(float(bucket.get(key, {}).get("revenue", Decimal("0.00"))))

    no_orders_data = sum(orders_series) == 0
    no_revenue_data = sum(revenue_series) == 0

    # Top products in the window
    top_map: dict[str, dict[str, Decimal | int | str]] = {}
    items = OrderItem.objects.filter(order__store=store, order__created_at__gte=since)
    for it in items:
        name = it.name or (it.product.name if it.product_id else "Product")
        rec = top_map.setdefault(name, {"name": name, "qty": 0, "revenue": Decimal("0.00")})
        rec["qty"] += int(it.quantity or 0)
        rec["revenue"] += (it.unit_price or Decimal("0.00")) * int(it.quantity or 0)
    top_products = sorted(top_map.values(), key=lambda r: (-int(r["qty"]), -float(r["revenue"])))[:10]

    context = {
        "store": store,
        "use_chartjs": use_chartjs,
        "days": days,
        "labels": labels,
        "orders_series": orders_series,
        "revenue_series": revenue_series,
        "no_orders_data": no_orders_data,
        "no_revenue_data": no_revenue_data,
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "product_count": product_count,
        "top_products": top_products,
    }
    return render(request, "merchant/reports.html", context)


# ===== Orders ===================================================================
@login_required
def order_list(request):
    store = _get_user_store_or_none(request)
    if not store:
        messages.info(request, "Create your store to view orders.")
        return redirect("merchant-profile")

    guard = _redirect_if_archived(request, store)
    if guard:
        return guard

    orders = store.orders.all().order_by("-created_at")
    return render(request, "merchant/orders.html", {"orders": orders, "page_obj": None})


@login_required
def order_detail(request, order_id: int):
    store = _get_user_store_or_none(request)
    if not store:
        messages.info(request, "Create your store to view orders.")
        return redirect("merchant-profile")

    order = get_object_or_404(Order, pk=order_id, store=store)
    return render(request, "merchant/order_detail.html", {"order": order})


# ===== Admin: stores ============================================================
@staff_required
def admin_store_list(request):
    stores = (
        Store.objects.select_related("owner")
        .prefetch_related("products", "orders")
        .order_by("-created_at")
    )
    return render(request, "merchant/stores_admin.html", {"stores": stores})


@staff_required
def admin_store_archive(request, store_id: int):
    store = get_object_or_404(Store, pk=store_id)
    if not store.is_archived:
        store.is_archived = True
        store.archived_at = timezone.now()
        store.save(update_fields=["is_archived", "archived_at"])
        messages.success(request, f"Store “{store.store_name}” archived.")
    else:
        messages.info(request, f"Store “{store.store_name}” is already archived.")
    return redirect("admin-store-list")


@staff_required
def admin_store_restore(request, store_id: int):
    store = get_object_or_404(Store, pk=store_id)
    if store.is_archived:
        store.is_archived = False
        store.archived_at = None
        store.save(update_fields=["is_archived", "archived_at"])
        messages.success(request, f"Store “{store.store_name}” restored.")
    else:
        messages.info(request, f"Store “{store.store_name}” is not archived.")
    return redirect("admin-store-list")


@staff_required
def admin_store_purge(request, store_id: int):
    store = get_object_or_404(Store, pk=store_id)

    if not store.is_archived or not store.archived_at:
        messages.error(request, "Store must be archived before it can be purged.")
        return redirect("admin-store-list")

    # Enforce 7-day window (604800 seconds)
    delta = timezone.now() - store.archived_at
    if delta.total_seconds() < 604800:
        remaining = 604800 - int(delta.total_seconds())
        days = remaining // 86400
        hours = (remaining % 86400) // 3600
        messages.warning(
            request,
            f"Too soon to purge. Try again in ~{days}d {hours}h (7 days after archive).",
        )
        return redirect("admin-store-list")

    name = store.store_name
    store.delete()
    messages.success(request, f"Store “{name}” permanently deleted.")
    return redirect("admin-store-list")


# ===== Merchant self-service archive/restore ===================================
@login_required
def merchant_store_archive(request):
    store = _get_user_store_or_none(request)
    if not store:
        messages.error(request, "No store found for your account.")
        return redirect("merchant-dashboard")

    if store.is_archived:
        messages.info(request, "Your store is already archived.")
        return redirect("merchant-profile")

    store.is_archived = True
    store.archived_at = timezone.now()
    store.save(update_fields=["is_archived", "archived_at"])
    messages.success(request, "Your store has been archived. You can restore it within 7 days.")
    return redirect("merchant-profile")


@login_required
def merchant_store_restore(request):
    store = _get_user_store_or_none(request)
    if not store:
        messages.error(request, "No store found for your account.")
        return redirect("merchant-dashboard")

    if not store.is_archived:
        messages.info(request, "Your store is not archived.")
        return redirect("merchant-profile")

    store.is_archived = False
    store.archived_at = None
    store.save(update_fields=["is_archived", "archived_at"])
    messages.success(request, "Your store has been restored.")
    return redirect("merchant-profile")


# ===== Products: create / edit / delete ========================================
@login_required
def add_product(request):
    store = _get_user_store_or_none(request)
    if not store:
        messages.error(request, "Create your store first.")
        return redirect("merchant-profile")

    guard = _redirect_if_archived(request, store)
    if guard:
        return guard

    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        description = (request.POST.get("description") or "").strip()
        image = request.FILES.get("image")

        # price (optional)
        price_val: Decimal | None = None
        price_raw = (request.POST.get("price") or "").strip()
        if price_raw:
            try:
                price_val = Decimal(price_raw)
            except (InvalidOperation, ValueError):
                messages.error(request, "Price must be a valid number.")
                return render(request, "merchant/add_product.html")

        if not name:
            messages.error(request, "Please provide a product name.")
            return render(request, "merchant/add_product.html")

        product = Product(store=store, name=name)
        if hasattr(Product, "price") and price_val is not None:
            product.price = price_val
        if hasattr(Product, "description"):
            product.description = description or ""
        if hasattr(Product, "image") and image:
            product.image = image

        product.save()
        messages.success(request, "Product created successfully.")
        return redirect("merchant-dashboard")

    # GET
    return render(request, "merchant/add_product.html")


@login_required
def edit_product(request, product_id: int):
    store = _get_user_store_or_none(request)
    if not store:
        messages.error(request, "Create your store first.")
        return redirect("merchant-profile")

    guard = _redirect_if_archived(request, store)
    if guard:
        return guard

    product = get_object_or_404(Product, pk=product_id, store=store)

    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        description = (request.POST.get("description") or "").strip()
        image = request.FILES.get("image")

        price_raw = (request.POST.get("price") or "").strip()
        if price_raw:
            try:
                price_val = Decimal(price_raw)
            except (InvalidOperation, ValueError):
                messages.error(request, "Price must be a valid number.")
                return render(request, "merchant/edit_product.html", {"product": product})
        else:
            price_val = None

        if not name:
            messages.error(request, "Please provide a product name.")
            return render(request, "merchant/edit_product.html", {"product": product})

        product.name = name
        if hasattr(Product, "description"):
            product.description = description or product.description
        if hasattr(Product, "price") and price_val is not None:
            product.price = price_val
        if hasattr(Product, "image") and image:
            product.image = image

        product.save()
        messages.success(request, "Product updated.")
        return redirect("merchant-dashboard")

    return render(request, "merchant/edit_product.html", {"product": product})


@login_required
def delete_product(request, product_id: int):
    store = _get_user_store_or_none(request)
    if not store:
        messages.error(request, "Create your store first.")
        return redirect("merchant-profile")

    guard = _redirect_if_archived(request, store)
    if guard:
        return guard

    product = get_object_or_404(Product, pk=product_id, store=store)

    if request.method == "POST":
        name = product.name
        product.delete()
        messages.success(request, f"Deleted “{name}”.")
        return redirect("merchant-dashboard")

    # Confirm screen
    return render(request, "merchant/confirm_delete.html", {"product": product})


# ===== CSV export for reports ===================================================
@login_required
def reports_export(request):
    store = _get_user_store_or_none(request)
    if not store:
        messages.info(request, "Create your store to export reports.")
        return redirect("merchant-profile")

    try:
        days = int(request.GET.get("range", "7"))
    except ValueError:
        days = 7
    days = days if days in (7, 30, 90) else 7

    since = timezone.now() - timedelta(days=days)
    orders = store.orders.filter(created_at__gte=since).order_by("created_at")

    filename = f"store_{store.id}_report_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(["Date", "Order ID", "Status", "Total", "Customer Email", "Items (qty)"])

    for o in orders:
        items_qty = o.items.aggregate(c=Sum("quantity"))["c"] or 0
        email = o.user.email if getattr(o, "user_id", None) and getattr(o.user, "email", "") else ""
        local_dt = o.created_at.astimezone(timezone.get_current_timezone()).strftime("%Y-%m-%d %H:%M")
        writer.writerow([local_dt, o.id, o.status, f"{o.total:.2f}", email, items_qty])

    return response


# ===== Payment Settings & simple Checkout demo =================================
@login_required
def payment_settings(request):
    store = _get_user_store_or_none(request)
    if not store:
        messages.error(request, "Create your store first.")
        return redirect("merchant-profile")

    methods = store.payment_methods.all()
    return render(request, "merchant/payment_settings.html", {"store": store, "methods": methods})


@login_required
def payment_method_create(request):
    store = _get_user_store_or_none(request)
    if not store:
        messages.error(request, "Create your store first.")
        return redirect("merchant-profile")

    if request.method == "POST":
        form = MerchantPaymentMethodForm(request.POST)
        if form.is_valid():
            pm = form.save(commit=False)
            pm.store = store
            pm.save()
            messages.success(request, "Payment method saved.")
            return redirect("merchant-payment-settings")
    else:
        form = MerchantPaymentMethodForm()

    return render(request, "merchant/payment_method_form.html", {"form": form})


@login_required
def payment_method_edit(request, method_id: int):
    store = _get_user_store_or_none(request)
    if not store:
        messages.error(request, "Create your store first.")
        return redirect("merchant-profile")

    pm = get_object_or_404(MerchantPaymentMethod, pk=method_id, store=store)

    if request.method == "POST":
        form = MerchantPaymentMethodForm(request.POST, instance=pm)
        if form.is_valid():
            form.save()
            messages.success(request, "Payment method updated.")
            return redirect("merchant-payment-settings")
    else:
        form = MerchantPaymentMethodForm(instance=pm)

    return render(request, "merchant/payment_method_form.html", {"form": form})


@login_required
def payment_method_delete(request, method_id: int):
    store = _get_user_store_or_none(request)
    if not store:
        messages.error(request, "Create your store first.")
        return redirect("merchant-profile")

    pm = get_object_or_404(MerchantPaymentMethod, pk=method_id, store=store)
    if request.method == "POST":
        pm.delete()
        messages.success(request, "Payment method deleted.")
    return redirect("merchant-payment-settings")


@login_required
def checkout_start(request):
    """
    Demo checkout entry-point: picks the store's default method (or the first active)
    and calls the adapter to get a redirect URL. Replace with your cart/amount logic.
    """
    store = _get_user_store_or_none(request)
    if not store:
        messages.error(request, "Create your store first.")
        return redirect("merchant-profile")

    pm = (
        store.payment_methods.filter(is_active=True, is_default=True).first()
        or store.payment_methods.filter(is_active=True).first()
    )
    if not pm:
        messages.error(request, "No active payment method. Add one in Payment Settings.")
        return redirect("merchant-payment-settings")

    # Example amount — replace with real cart total
    amount_cents = 2599
    currency = "usd"

    success_url = request.build_absolute_uri(reverse("merchant-checkout-success"))
    cancel_url = request.build_absolute_uri(reverse("merchant-checkout-cancel"))
    adapter = build_adapter(
        pm.provider,
        credentials=pm.credentials,
        success_url=success_url,
        cancel_url=cancel_url,
    )

    result = adapter.start_checkout(
        amount_cents=amount_cents,
        currency=currency,
        metadata={"store_id": store.id, "order_id": "demo"},
    )
    return redirect(result["redirect_url"])


@login_required
def checkout_success(request):
    messages.success(request, "Payment approved (demo). You can fulfill the order now.")
    return redirect("merchant-dashboard")


@login_required
def checkout_cancel(request):
    messages.warning(request, "Payment canceled.")
    return redirect("merchant-dashboard")


# ===== Plans (pricing + checkout) ==============================================
PLAN_PRICES = {
    # cents
    "starter": 900,
    "pro": 2900,
    "elite": 7900,
}


@login_required
def plan_pricing(request):
    store = _get_user_store_or_none(request)
    if not store:
        messages.info(request, "Create your store to continue.")
        return redirect("merchant-profile")

    methods = list(store.payment_methods.filter(is_active=True).order_by("-is_default", "provider"))
    return render(request, "merchant/plans.html", {"store": store, "methods": methods})


@login_required
def plan_checkout(request, plan_slug: str):
    plan = (plan_slug or "").lower()
    if plan not in PLAN_PRICES:
        messages.error(request, "Unknown plan.")
        return redirect("merchant-plans")

    store = _get_user_store_or_none(request)
    if not store:
        messages.info(request, "Create your store to continue.")
        return redirect("merchant-profile")

    provider = (request.GET.get("provider") or "").lower()

    # choose payment method: explicit provider > default active > any active
    if provider:
        pm = store.payment_methods.filter(is_active=True, provider=provider).first()
        if not pm:
            messages.error(request, f"{provider.title()} is not active for this store.")
            return redirect("merchant-payment-settings")
    else:
        pm = (
            store.payment_methods.filter(is_active=True, is_default=True).first()
            or store.payment_methods.filter(is_active=True).first()
        )

    if not pm:
        messages.error(request, "No active payment method. Add one in Payment Settings.")
        return redirect("merchant-payment-settings")

    amount_cents = PLAN_PRICES[plan]
    currency = "usd"

    success_url = request.build_absolute_uri(f"{reverse('merchant-plan-success')}?plan={plan}")
    cancel_url = request.build_absolute_uri(reverse("merchant-plan-cancel"))

    adapter = build_adapter(pm.provider, credentials=pm.credentials, success_url=success_url, cancel_url=cancel_url)
    result = adapter.start_checkout(
        amount_cents=amount_cents,
        currency=currency,
        metadata={"store_id": store.id, "plan": plan, "purchase_type": "subscription"},
    )
    return redirect(result["redirect_url"])


@login_required
def plan_checkout_success(request):
    store = _get_user_store_or_none(request)
    if not store:
        messages.info(request, "Create your store to continue.")
        return redirect("merchant-profile")

    plan = (request.GET.get("plan") or "").lower()
    if plan not in PLAN_PRICES:
        messages.warning(request, "Payment approved (demo), but plan was unknown.")
        return redirect("merchant-dashboard")

    # In a real implementation you would validate via session/webhook; this is demo.
    store.plan = plan
    store.save(update_fields=["plan"])
    messages.success(request, f"Your plan has been updated to {plan.title()}.")
    return redirect("merchant-dashboard")


@login_required
def plan_checkout_cancel(request):
    messages.warning(request, "Plan checkout canceled.")
    return redirect("merchant-plans")


# ===== Admin: all payment methods ==============================================
@staff_required
def admin_payment_methods(request):
    methods = (
        MerchantPaymentMethod.objects.select_related("store", "store__owner")
        .order_by("store__store_name", "-is_default", "provider")
    )
    return render(request, "merchant/admin_payment_methods.html", {"methods": methods})


# ===== Webhook stubs (Stripe / PayPal) =========================================
def _json(request):
    try:
        return json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return None


@csrf_exempt
def webhook_stripe(request):
    """
    Stripe webhook stub.
    Set STRIPE_WEBHOOK_SECRET in settings/env for signature verification later.
    """
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    payload = request.body
    sig_header = request.headers.get("Stripe-Signature")

    # NOTE: real verification requires stripe package:
    # import stripe
    # stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)

    if not sig_header:
        # keep permissive in dev; tighten in prod
        pass

    event = _json(request)
    if event is None:
        return HttpResponseBadRequest("Invalid JSON")

    # Example routing (expand with your business logic)
    event_type = event.get("type")
    data = event.get("data", {}).get("object", {})
    # store_id = (data.get("metadata") or {}).get("store_id")

    return HttpResponse(status=200)


@csrf_exempt
def webhook_paypal(request):
    """
    PayPal webhook stub.
    Set PAYPAL_WEBHOOK_ID in settings/env for verification later.
    """
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    # Real verification calls PayPal's "Verify webhook signature" endpoint.
    event = _json(request)
    if event is None:
        return HttpResponseBadRequest("Invalid JSON")

    # Example routing
    event_type = event.get("event_type")
    resource = event.get("resource", {})
    # store_id = (resource.get("custom_id") or resource.get("supplementary_data", {}).get("related_ids", {}).get("store_id"))

    return HttpResponse(status=200)
