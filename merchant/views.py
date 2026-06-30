from __future__ import annotations

from datetime import timedelta
from decimal import Decimal, InvalidOperation
from django.core.mail import send_mail
import csv
import hashlib
import hmac
import io
import json

import qrcode
import stripe
from django.contrib.auth import get_user_model


from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import models
from django.db.models import Sum
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .models import (
    MallZone,
    MerchantStore,
    StoreCategory,
    Product,
    Order,
    OrderItem,
    MerchantPaymentMethod,
)

from .forms import StoreForm, MerchantPaymentMethodForm
from .payments.adapters import build_adapter
from customer.models import CustomerProfile, CustomerAddress
from delivery.models import DeliveryJob

Store = MerchantStore


def staff_required(view_func):
    return login_required(
        user_passes_test(lambda u: u.is_staff or u.is_superuser)(view_func)
    )


def merchant_nav_context(request):
    if not request.user.is_authenticated:
        return {}

    stores = Store.objects.filter(owner=request.user, is_archived=False).order_by("created_at")
    current_store = get_current_store(request)

    return {
        "nav_stores": stores,
        "nav_current_store": current_store,
    }


def _get_user_store_or_none(request):
    try:
        return Store.objects.select_related("owner").get(owner=request.user)
    except Store.DoesNotExist:
        return None


def _redirect_if_archived(request, store: Store | None):
    if store and getattr(store, "is_archived", False):
        messages.warning(
            request,
            "This store is archived. Some actions are disabled until it is restored.",
        )
        return redirect("merchant-profile")
    return None


def get_current_store(request):
    if not request.user.is_authenticated:
        return None

    qs = Store.objects.filter(owner=request.user, is_archived=False).order_by("created_at")

    store_id = request.GET.get("store")
    if store_id:
        try:
            store = qs.get(pk=int(store_id))
            request.session["active_store_id"] = store.id
            return store
        except (ValueError, Store.DoesNotExist):
            pass

    sid = request.session.get("active_store_id")
    if sid:
        try:
            return qs.get(pk=int(sid))
        except (ValueError, Store.DoesNotExist):
            request.session.pop("active_store_id", None)

    store = qs.first()
    if store:
        request.session["active_store_id"] = store.id
    return store


def ensure_default_payment_methods(store: MerchantStore):
    stripe_method, _ = MerchantPaymentMethod.objects.get_or_create(
        store=store,
        provider="stripe",
        defaults={
            "is_active": True,
            "is_default": True,
            "credentials": {},
        },
    )

    paypal_method, _ = MerchantPaymentMethod.objects.get_or_create(
        store=store,
        provider="paypal",
        defaults={
            "is_active": True,
            "is_default": False,
            "credentials": {},
        },
    )

    coinbase_method, _ = MerchantPaymentMethod.objects.get_or_create(
        store=store,
        provider="coinbase",
        defaults={
            "is_active": True,
            "is_default": False,
            "credentials": {},
        },
    )

    changed = False

    if not stripe_method.is_active:
        stripe_method.is_active = True
        changed = True

    if not paypal_method.is_active:
        paypal_method.is_active = True
        changed = True

    if not coinbase_method.is_active:
        coinbase_method.is_active = True
        changed = True

    if not MerchantPaymentMethod.objects.filter(store=store, is_default=True).exists():
        stripe_method.is_default = True
        changed = True

    if changed:
        stripe_method.save()
        paypal_method.save()
        coinbase_method.save()


PROMO_CODES = {
    "SAVE10": {"kind": "percent", "value": Decimal("10.00"), "label": "10% off"},
    "WELCOME5": {"kind": "fixed", "value": Decimal("5.00"), "label": "$5 off"},
}


def build_public_url(request, path):
    base = (getattr(settings, "PUBLIC_BASE_URL", "") or "").rstrip("/")
    if base:
        return f"{base}{path}"
    return request.build_absolute_uri(path)


def _calculate_checkout_context(request):
    cart = request.session.get("cart", {})
    promo_code = (request.session.get("promo_code") or "").strip().upper()

    items = []
    subtotal = Decimal("0.00")
    discount = Decimal("0.00")
    total = Decimal("0.00")
    store_id = None
    store = None
    payment_methods = []
    promo = PROMO_CODES.get(promo_code)

    for key, item in cart.items():
        item_store_id = item.get("store_id")

        if store_id is None:
            store_id = item_store_id
        elif item_store_id != store_id:
            return {"error": "Your cart contains items from multiple stores. Please use one store at a time."}

        price = Decimal(str(item.get("price", "0.00")))
        quantity = int(item.get("quantity", 0))
        line_total = price * quantity
        subtotal += line_total

        items.append({
            "key": key,
            "product_id": key,
            "name": item.get("name", "Item"),
            "price": price,
            "quantity": quantity,
            "line_total": line_total,
            "store_slug": item.get("store_slug", ""),
        })

    if promo and subtotal > 0:
        if promo["kind"] == "percent":
            discount = (subtotal * promo["value"] / Decimal("100")).quantize(Decimal("0.01"))
        else:
            discount = min(subtotal, promo["value"])

    total = max(Decimal("0.00"), subtotal - discount)

    if store_id:
        store = get_object_or_404(MerchantStore, pk=store_id)
        ensure_default_payment_methods(store)
        payment_methods = list(
            store.payment_methods.filter(is_active=True).order_by("-is_default", "provider")
        )

    return {
        "cart": cart,
        "items": items,
        "subtotal": subtotal,
        "discount": discount,
        "total": total,
        "store": store,
        "payment_methods": payment_methods,
        "promo_code": promo_code,
    }

from django.contrib import messages
from django.shortcuts import render, redirect

def build_onboarding_checklist(store):
    has_logo = bool(getattr(store, "logo", None))
    has_contact_person = bool((getattr(store, "contact_person", "") or "").strip())
    has_contact_email = bool((getattr(store, "contact_email", "") or "").strip())
    has_contact_phone = bool((getattr(store, "contact_phone", "") or "").strip())
    has_contact_info = has_contact_person and has_contact_email and has_contact_phone
    has_product = store.products.exists() if hasattr(store, "products") else False
    is_live = bool(getattr(store, "is_public", False))

    items = [
        {
            "label": "Upload your logo",
            "done": has_logo,
            "hint": "Add a logo so your storefront stands out in the directory and on your store page.",
        },
        {
            "label": "Add vendor contact info",
            "done": has_contact_info,
            "hint": "Add contact person, email, and phone so mall management can reach you quickly.",
        },
        {
            "label": "Add your first product",
            "done": has_product,
            "hint": "Create at least one product so your store is ready for visitors.",
        },
        {
            "label": "Publish your storefront",
            "done": is_live,
            "hint": "Turn on Public Storefront so shoppers can visit your store.",
        },
    ]

    completed = sum(1 for item in items if item["done"])
    total = len(items)
    percent = int((completed / total) * 100) if total else 0

    return {
        "items": items,
        "completed": completed,
        "total": total,
        "percent": percent,
        "all_done": completed == total,
    }


@login_required
def profile(request):
    store = get_current_store(request)
    if not store:
        store = MerchantStore.objects.create(
            owner=request.user,
            store_name="",
            category="",
            plan="starter",
        )
        request.session["active_store_id"] = store.id
        ensure_default_payment_methods(store)

    if request.method == "POST":
        form = StoreForm(request.POST, request.FILES, instance=store)
        if form.is_valid():
            store = form.save(commit=False)

            if hasattr(store, "offers_local_delivery"):
                store.offers_local_delivery = request.POST.get("offers_local_delivery") == "on"
                store.offers_pickup = request.POST.get("offers_pickup") == "on"
                store.offers_shipping = request.POST.get("offers_shipping") == "on"
                store.business_zip = (request.POST.get("business_zip") or "").strip()

                try:
                    store.delivery_radius_miles = max(0, int(request.POST.get("delivery_radius_miles") or 0))
                except (TypeError, ValueError):
                    store.delivery_radius_miles = store.delivery_radius_miles or 0

                try:
                    store.delivery_fee = Decimal(request.POST.get("delivery_fee") or "0")
                except Exception:
                    store.delivery_fee = Decimal("0.00")

                try:
                    store.delivery_minimum = Decimal(request.POST.get("delivery_minimum") or "0")
                except Exception:
                    store.delivery_minimum = Decimal("0.00")

                try:
                    store.average_prep_minutes = max(0, int(request.POST.get("average_prep_minutes") or 0))
                except (TypeError, ValueError):
                    store.average_prep_minutes = store.average_prep_minutes or 30

            store.save()
            form.save_m2m()

            ensure_default_payment_methods(store)
            messages.success(request, "Store profile saved.")
            return redirect("merchant-profile")
    else:
        form = StoreForm(instance=store)

    ensure_default_payment_methods(store)
    CustomerProfile.objects.get_or_create(user=request.user)

    public_url = None
    qr_url = None
    if store and getattr(store, "slug", None):
        base = (getattr(settings, "PUBLIC_BASE_URL", "") or request.build_absolute_uri("/")).rstrip("/")
        public_url = f"{base}{reverse('storefront', args=[store.slug])}"
        qr_url = reverse("storefront-qr", args=[store.slug])

    onboarding = build_onboarding_checklist(store)

    return render(
        request,
        "merchant/profile.html",
        {
            "store": store,
            "form": form,
            "public_url": public_url,
            "qr_url": qr_url,
            "onboarding": onboarding,
        },
    )

def _build_success_context_from_order(order: Order, session, payment_label: str):
    promo_code = ""
    customer_name = ""
    customer_email = ""

    try:
        metadata = session["metadata"]
    except Exception:
        metadata = None

    if metadata:
        try:
            promo_code = metadata["promo_code"] or ""
        except Exception:
            promo_code = ""

        try:
            customer_name = metadata["customer_name"] or ""
        except Exception:
            customer_name = ""

        try:
            customer_email = metadata["customer_email"] or ""
        except Exception:
            customer_email = ""

    items = []
    subtotal = Decimal("0.00")

    for item in order.items.all():
        unit_price = item.unit_price or Decimal("0.00")
        quantity = int(item.quantity or 0)
        line_total = unit_price * quantity
        subtotal += line_total

        items.append({
            "name": item.name or (item.product.name if getattr(item, "product_id", None) else "Item"),
            "quantity": quantity,
            "price": f"{unit_price:.2f}",
            "line_total": f"{line_total:.2f}",
        })

    discount = Decimal("0.00")
    total = order.total if order.total is not None else subtotal

    if subtotal > total:
        discount = (subtotal - total).quantize(Decimal("0.01"))

    return {
        "customer_name": customer_name,
        "customer_email": customer_email,
        "store_name": order.store.store_name if order.store_id else "",
        "store_slug": getattr(order.store, "slug", "") if order.store_id else "",
        "items": items,
        "subtotal": f"{subtotal:.2f}",
        "discount": f"{discount:.2f}",
        "total": f"{total:.2f}",
        "promo_code": promo_code,
        "payment_label": payment_label,
    }


def _mark_order_paid_from_checkout_session(session):
    if not session:
        return None

    order_id = None

    try:
        metadata = session["metadata"]
    except Exception:
        metadata = None

    if metadata:
        try:
            order_id = metadata["order_id"]
        except Exception:
            order_id = None

    if not order_id:
        try:
            order_id = session["client_reference_id"]
        except Exception:
            order_id = None

    if not order_id:
        return None

    try:
        order = Order.objects.get(pk=int(order_id))
    except (ValueError, TypeError, Order.DoesNotExist):
        return None

    payment_status = ""
    status = ""

    try:
        payment_status = session["payment_status"] or ""
    except Exception:
        payment_status = ""

    try:
        status = session["status"] or ""
    except Exception:
        status = ""

    if payment_status == "paid" or status == "complete":
        if order.status != "paid":
            order.status = "paid"
            order.save(update_fields=["status"])

    return order


@login_required
def switch_store(request, store_id: int):
    try:
        store = Store.objects.get(pk=store_id, owner=request.user, is_archived=False)
    except Store.DoesNotExist:
        messages.error(request, "Store not found or not accessible.")
        return redirect("merchant-dashboard")

    request.session["active_store_id"] = store.id
    messages.success(request, f'Switched to "{store.store_name}".')
    return redirect(request.META.get("HTTP_REFERER") or reverse("merchant-dashboard"))


@staff_required
def admin_payment_methods(request):
    methods = (
        MerchantPaymentMethod.objects
        .select_related("store", "store__owner")
        .order_by("store__store_name", "-is_default", "provider")
    )
    return render(request, "merchant/admin_payment_methods.html", {"methods": methods})


def storefront(request, slug: str):
    store = get_object_or_404(
        Store.objects.prefetch_related("products"),
        slug=slug,
    )

    if store.is_archived or not store.is_public:
        raise Http404("Store not available")

    products = store.products.all().order_by("-created_at")

    base = (getattr(settings, "PUBLIC_BASE_URL", "") or request.build_absolute_uri("/")).rstrip("/")
    public_url = f"{base}{reverse('storefront', args=[slug])}"
    qr_url = reverse("storefront-qr", args=[slug])

    return render(
        request,
        "merchant/storefront.html",
        {
            "store": store,
            "products": products,
            "public_url": public_url,
            "qr_url": qr_url,
        },
    )


def product_detail(request, slug: str, product_id: int):
    store = get_object_or_404(
        Store.objects.prefetch_related("products"),
        slug=slug,
    )

    if store.is_archived or not store.is_public:
        raise Http404("Store not available")

    product = get_object_or_404(Product, pk=product_id, store=store)

    base = (getattr(settings, "PUBLIC_BASE_URL", "") or request.build_absolute_uri("/")).rstrip("/")
    public_url = f"{base}{reverse('product-detail', args=[slug, product.id])}"

    return render(
        request,
        "merchant/product_detail.html",
        {
            "store": store,
            "product": product,
            "public_url": public_url,
        },
    )


def storefront_qr(request, slug: str):
    store = get_object_or_404(Store, slug=slug)

    if store.is_archived or not store.is_public:
        raise Http404("Store not available")

    base = (getattr(settings, "PUBLIC_BASE_URL", "") or request.build_absolute_uri("/")).rstrip("/")
    target_url = f"{base}{reverse('storefront', args=[slug])}"

    def _to_int(v, default, lo, hi):
        try:
            n = int(v)
            return max(lo, min(hi, n))
        except (TypeError, ValueError):
            return default

    box_size = _to_int(request.GET.get("size"), 6, 2, 20)
    border = 4 if (request.GET.get("box") or "").strip().lower() in {"1", "true", "yes", "on"} else 1

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(target_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    resp = HttpResponse(buf.read(), content_type="image/png")
    resp["Cache-Control"] = "public, max-age=86400"
    if (request.GET.get("download") or "").strip().lower() in {"1", "true", "yes", "on"}:
        resp["Content-Disposition"] = f'attachment; filename="majicmall-store-{store.slug}.png"'
    return resp



def product_has_stock(product, quantity=1):
    if not getattr(product, "track_inventory", False):
        return True

    return int(getattr(product, "stock_quantity", 0) or 0) >= int(quantity or 1)


def decrement_inventory_for_order(order):
    for item in order.items.select_related("product").all():
        product = item.product

        if not product:
            continue

        if not getattr(product, "track_inventory", False):
            continue

        qty = int(item.quantity or 0)
        current_stock = int(product.stock_quantity or 0)
        product.stock_quantity = max(0, current_stock - qty)
        product.save(update_fields=["stock_quantity"])


def cart_add(request, product_id: int):
    if request.method != "POST":
        return redirect("mall-directory")

    product = get_object_or_404(Product, pk=product_id)

    if not product_has_stock(product, 1):
        messages.warning(request, "This item is currently out of stock.")
        return redirect("product-detail", slug=product.store.slug, product_id=product.id)

    cart = request.session.get("cart", {})
    key = str(product.id)

    existing_store_id = None
    if cart:
        first_item = next(iter(cart.values()))
        existing_store_id = first_item.get("store_id")

    if existing_store_id and int(existing_store_id) != int(product.store_id):
        messages.warning(
            request,
            "Your cart already contains items from another store. Please finish checkout or clear that cart before adding items from a different store."
        )
        return redirect("cart-view")

    if key in cart:
        new_quantity = int(cart[key].get("quantity", 0)) + 1

        if not product_has_stock(product, new_quantity):
            messages.warning(request, "Not enough inventory is available for that quantity.")
            return redirect("cart-view")

        cart[key]["quantity"] = new_quantity
    else:
        cart[key] = {
            "name": product.name,
            "quantity": 1,
            "price": str(product.price) if getattr(product, "price", None) is not None else "0.00",
            "store_id": product.store_id,
            "store_slug": product.store.slug,
            "image_url": product.image.url if getattr(product, "image", None) else "",
        }

    request.session["cart"] = cart
    request.session["last_store_slug"] = product.store.slug
    request.session.modified = True

    messages.success(request, f"{product.name} added to cart.")
    return redirect("cart-view")


def cart_remove(request, product_id: int):
    if request.method != "POST":
        return redirect("cart-view")

    cart = request.session.get("cart", {})
    key = str(product_id)

    if key in cart:
        removed_name = cart[key].get("name", "Item")
        del cart[key]
        request.session["cart"] = cart

        if cart:
            first_item = next(iter(cart.values()))
            request.session["last_store_slug"] = first_item.get("store_slug", "")
        else:
            request.session.pop("last_store_slug", None)
            request.session.pop("promo_code", None)

        request.session.modified = True
        messages.success(request, f"{removed_name} removed from cart.")
    else:
        messages.warning(request, "Item was not found in your cart.")

    return redirect("cart-view")


def cart_view(request):
    cart = request.session.get("cart", {})
    last_store_slug = request.session.get("last_store_slug")

    total = Decimal("0.00")
    for item in cart.values():
        price = Decimal(str(item.get("price", "0.00")))
        quantity = int(item.get("quantity", 0))
        total += price * quantity

    return render(
        request,
        "merchant/cart.html",
        {
            "cart": cart,
            "last_store_slug": last_store_slug,
            "total": total,
        },
    )


def public_checkout(request):
    context = _calculate_checkout_context(request)

    if context.get("error"):
        messages.error(request, context["error"])
        return redirect("cart-view")

    return render(request, "merchant/public_checkout.html", context)


def public_checkout_apply_promo(request):
    if request.method != "POST":
        return redirect("public-checkout")

    context = _calculate_checkout_context(request)
    if context.get("error"):
        messages.error(request, context["error"])
        return redirect("cart-view")

    if not context["items"]:
        messages.warning(request, "Your cart is empty.")
        return redirect("cart-view")

    if request.POST.get("clear_promo") == "1":
        request.session.pop("promo_code", None)
        request.session.modified = True
        messages.success(request, "Promo code removed.")
        return redirect("public-checkout")

    promo_code = (request.POST.get("promo_code") or "").strip().upper()

    if not promo_code:
        request.session.pop("promo_code", None)
        request.session.modified = True
        messages.warning(request, "Please enter a promo code.")
        return redirect("public-checkout")

    if promo_code not in PROMO_CODES:
        messages.error(request, "That promo code is not valid.")
        return redirect("public-checkout")

    request.session["promo_code"] = promo_code
    request.session.modified = True
    messages.success(request, f"Promo code {promo_code} applied.")
    return redirect("public-checkout")


def public_checkout_submit(request):
    if request.method != "POST":
        return redirect("public-checkout")

    context = _calculate_checkout_context(request)

    if context.get("error"):
        messages.error(request, context["error"])
        return redirect("cart-view")

    if not context["items"]:
        messages.warning(request, "Your cart is empty.")
        return redirect("cart-view")

    customer_name = (request.POST.get("customer_name") or "").strip()
    customer_email = (request.POST.get("customer_email") or "").strip()
    customer_phone = (request.POST.get("customer_phone") or "").strip()

    shipping_address = (request.POST.get("shipping_address") or "").strip()
    shipping_city = (request.POST.get("shipping_city") or "").strip()
    shipping_state = (request.POST.get("shipping_state") or "").strip()
    shipping_zip = (request.POST.get("shipping_zip") or "").strip()
    delivery_notes = (request.POST.get("delivery_notes") or "").strip()

    payment_method_id = (request.POST.get("payment_method_id") or "").strip()
    fulfillment_method = (request.POST.get("fulfillment_method") or "shipping").strip().lower()

    allowed_fulfillment = []

    if getattr(context["store"], "offers_pickup", False):
        allowed_fulfillment.append("pickup")

    if getattr(context["store"], "offers_local_delivery", False):
        allowed_fulfillment.append("local_delivery")

    if getattr(context["store"], "offers_shipping", False):
        allowed_fulfillment.append("shipping")

    if not allowed_fulfillment:
        allowed_fulfillment = ["shipping"]

    if fulfillment_method not in allowed_fulfillment:
        messages.error(request, "Please select a valid delivery option.")
        return redirect("public-checkout")

    if (
        not customer_name
        or not customer_email
        or not shipping_address
        or not shipping_city
        or not shipping_state
        or not shipping_zip
    ):
        messages.error(request, "Please complete all required customer and shipping fields.")
        return redirect("public-checkout")

    if not payment_method_id:
        messages.error(request, "Please select a payment method.")
        return redirect("public-checkout")

    store = context["store"]
    total = context["total"]
    subtotal = total

    try:
        payment_method = store.payment_methods.get(pk=int(payment_method_id), is_active=True)
    except (ValueError, MerchantPaymentMethod.DoesNotExist):
        messages.error(request, "Invalid payment method selected.")
        return redirect("public-checkout")

    order = Order.objects.create(
        store=store,
        total=total,
        status="pending",

        customer_name=customer_name,
        customer_email=customer_email,
        customer_phone=customer_phone,

        shipping_address=shipping_address,
        shipping_city=shipping_city,
        shipping_state=shipping_state,
        shipping_zip=shipping_zip,
        delivery_notes=delivery_notes,
        fulfillment_method=fulfillment_method,
    )

    for item in context["items"]:
        product_obj = None
        try:
            product_obj = Product.objects.get(pk=int(item["product_id"]))
        except (ValueError, Product.DoesNotExist):
            product_obj = None

        OrderItem.objects.create(
            order=order,
            product=product_obj,
            name=item["name"],
            quantity=item["quantity"],
            unit_price=item["price"],
        )

    success_url = build_public_url(request, f"{reverse('public-checkout-success')}?order_id={order.id}")
    cancel_url = build_public_url(request, reverse("public-checkout-cancel"))

    adapter = build_adapter(
        payment_method.provider,
        credentials=payment_method.credentials,
        success_url=success_url,
        cancel_url=cancel_url,
    )

    result = adapter.start_checkout(
        amount_cents=int(total * 100),
        currency="usd",
        metadata={
            "order_id": str(order.id),
            "store_id": str(store.id),
            "customer_name": customer_name,
            "customer_email": customer_email,
            "customer_phone": customer_phone,
            "shipping_address": shipping_address,
            "shipping_city": shipping_city,
            "shipping_state": shipping_state,
            "shipping_zip": shipping_zip,
            "promo_code": context.get("promo_code", ""),
            "purchase_type": "storefront_order",
            "fulfillment_method": fulfillment_method,
        },
    )

    request.session["checkout_customer_name"] = customer_name
    request.session["checkout_customer_email"] = customer_email
    request.session["checkout_order_id"] = order.id
    request.session.modified = True

    return redirect(result["redirect_url"])
def create_delivery_job_for_order(order):
    if getattr(order, "fulfillment_method", "") != "local_delivery":
        return None

    job, created = DeliveryJob.objects.get_or_create(
        order=order,
        defaults={
            "store": order.store,
            "status": "pending",
            "pickup_zip": getattr(order.store, "business_zip", "") or "",
            "delivery_zip": getattr(order, "shipping_zip", "") or "",
            "delivery_fee": getattr(order.store, "delivery_fee", 0) or 0,
            "delivery_notes": getattr(order, "delivery_notes", "") or "",
        },
    )

    return job


def ensure_customer_account_from_order(order):
    customer_email = (getattr(order, "customer_email", "") or "").strip().lower()
    customer_name = (getattr(order, "customer_name", "") or "").strip()

    if not customer_email:
        return None

    User = get_user_model()

    user, created = User.objects.get_or_create(
        email=customer_email,
        defaults={
            "username": customer_email,
            "first_name": customer_name.split(" ")[0] if customer_name else "",
            "last_name": " ".join(customer_name.split(" ")[1:]) if len(customer_name.split(" ")) > 1 else "",
        },
    )

    if created:
        user.set_unusable_password()
        user.save()

    profile, _ = CustomerProfile.objects.get_or_create(user=user)

    shipping_address = (getattr(order, "shipping_address", "") or "").strip()
    shipping_city = (getattr(order, "shipping_city", "") or "").strip()
    shipping_state = (getattr(order, "shipping_state", "") or "").strip()
    shipping_zip = (getattr(order, "shipping_zip", "") or "").strip()

    if shipping_address and shipping_city and shipping_state and shipping_zip:
        if not profile.addresses.exists():
            CustomerAddress.objects.create(
                customer=profile,
                nickname="Primary",
                full_name=customer_name or customer_email,
                address1=shipping_address,
                city=shipping_city,
                state=shipping_state,
                postal_code=shipping_zip,
                default=True,
            )

    return profile


def send_order_confirmation_emails(order, customer_name="", customer_email=""):
    ensure_customer_account_from_order(order)

    store = order.store
    store_name = getattr(store, "store_name", "MajicMall Megaverse Store")
    items = order.items.all()

    item_lines = [
        f"- {item.name} x {item.quantity} @ ${item.unit_price}"
        for item in items
    ]

    items_text = "\n".join(item_lines) if item_lines else "No items listed."
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@majicmall.com")

    store_email = (
        getattr(store, "contact_email", None)
        or getattr(getattr(store, "owner", None), "email", None)
    )

    if customer_email:
        send_mail(
            subject=f"MajicMall Megaverse Order Confirmation #{order.id}",
            message=(
                f"Hello {customer_name or 'MajicMall Customer'},\n\n"
                f"Thank you for your order from {store_name}!\n\n"
                f"Order Number: #{order.id}\n"
                f"Order Total: ${order.total}\n\n"
                f"Items:\n{items_text}\n\n"
                f"Your MajicMall Megaverse Customer Command Center is ready.\n"
                f"Visit your account to view orders, track shipments, save addresses, and earn rewards.\n"
                f"Customer Account: /customer/\n\n"
                f"Thank you for shopping inside the MajicMall Megaverse."
            ),
            from_email=from_email,
            recipient_list=[customer_email],
            fail_silently=True,
        )

    if store_email:
        send_mail(
            subject=f"New MajicMall Megaverse Order #{order.id}",
            message=(
                f"New order received for {store_name}.\n\n"
                f"Order Number: #{order.id}\n"
                f"Customer: {customer_name or 'Customer'}\n"
                f"Customer Email: {customer_email or 'Not provided'}\n"
                f"Order Total: ${order.total}\n\n"
                f"Items:\n{items_text}\n\n"
                f"Log in to your merchant dashboard to view the order."
            ),
            from_email=from_email,
            recipient_list=[store_email],
            fail_silently=True,
        )


def public_checkout_success(request):
    gateway = (request.GET.get("gateway") or "").strip().lower()
    paypal_token = (request.GET.get("token") or "").strip()
    session_id = (request.GET.get("session_id") or "").strip()

    if gateway == "paypal" or paypal_token:
        order_id = request.GET.get("order_id") or request.session.get("checkout_order_id")

        if not order_id:
            messages.warning(request, "Payment completed, but no order was found in your session.")
            return redirect("mall-directory")

        order = get_object_or_404(
            Order.objects.select_related("store").prefetch_related("items"),
            pk=order_id,
        )

        payment_method = order.store.payment_methods.filter(
            provider="paypal",
            is_active=True,
        ).first()

        if not payment_method:
            messages.error(request, "PayPal is not configured for this store.")
            return redirect("mall-directory")

        try:
            adapter = build_adapter(
                "paypal",
                credentials=payment_method.credentials,
                success_url=build_public_url(request, reverse("public-checkout-success")),
                cancel_url=build_public_url(request, reverse("public-checkout-cancel")),
            )
            paypal_result = adapter.capture_checkout(paypal_token)
        except Exception as e:
            print("PAYPAL CAPTURE ERROR:", repr(e))
            messages.error(request, "PayPal payment verification failed.")
            return redirect("mall-directory")

        if paypal_result.get("status") == "COMPLETED":
            if order.status != "paid":
                order.status = "paid"
                order.save(update_fields=["status"])

            customer_name = request.session.get("checkout_customer_name", "")
            customer_email = request.session.get("checkout_customer_email", "")

            decrement_inventory_for_order(order)
            create_delivery_job_for_order(order)

            send_order_confirmation_emails(
                order=order,
                customer_name=customer_name,
                customer_email=customer_email,
            )
        else:
            messages.error(request, "PayPal payment was not completed.")
            return redirect("mall-directory")

        payment_label = "PayPal"

        request.session["cart"] = {}
        request.session.pop("last_store_slug", None)
        request.session.pop("promo_code", None)
        request.session.pop("checkout_customer_name", None)
        request.session.pop("checkout_customer_email", None)
        request.session.pop("checkout_order_id", None)
        request.session.modified = True

        fake_session = {
            "metadata": {
                "customer_name": customer_name,
                "customer_email": customer_email,
                "promo_code": "",
            }
        }

        context = _build_success_context_from_order(order, fake_session, payment_label)
        return render(request, "merchant/checkout_success.html", context)

    if not session_id:
        messages.warning(request, "Missing checkout session.")
        return redirect("mall-directory")

    stripe.api_key = settings.STRIPE_SECRET_KEY

    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except Exception as e:
        print("STRIPE SESSION RETRIEVE ERROR:", repr(e))
        messages.error(request, "Payment verification failed.")
        return redirect("mall-directory")

    order = _mark_order_paid_from_checkout_session(session)

    if not order:
        messages.error(request, "Order not found.")
        return redirect("mall-directory")

    metadata = session.get("metadata", {}) or {}

    customer_name = (
        metadata.get("customer_name")
        or request.session.get("checkout_customer_name", "")
    )

    customer_email = (
        metadata.get("customer_email")
        or request.session.get("checkout_customer_email", "")
    )

    if order.status == "paid":
        decrement_inventory_for_order(order)
        create_delivery_job_for_order(order)

        send_order_confirmation_emails(
            order=order,
            customer_name=customer_name,
            customer_email=customer_email,
        )

    payment_label = "Credit / Debit Card"

    request.session["cart"] = {}
    request.session.pop("last_store_slug", None)
    request.session.pop("promo_code", None)
    request.session.pop("checkout_customer_name", None)
    request.session.pop("checkout_customer_email", None)
    request.session.pop("checkout_order_id", None)
    request.session.modified = True

    context = _build_success_context_from_order(order, session, payment_label)
    return render(request, "merchant/checkout_success.html", context)


def public_checkout_cancel(request):
    messages.warning(request, "Checkout canceled.")
    return redirect("cart-view")


@login_required
def category_list(request):
    store = get_current_store(request)
    if not store:
        messages.error(request, "Create your store first.")
        return redirect("merchant-profile")

    guard = _redirect_if_archived(request, store)
    if guard:
        return guard

    categories = store.categories.all()
    return render(request, "merchant/category_list.html", {"store": store, "categories": categories})


@login_required
def add_category(request):
    store = get_current_store(request)
    if not store:
        messages.error(request, "Create your store first.")
        return redirect("merchant-profile")

    guard = _redirect_if_archived(request, store)
    if guard:
        return guard

    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()

        if not name:
            messages.error(request, "Please provide a category name.")
            return render(request, "merchant/add_category.html", {"store": store})

        StoreCategory.objects.create(store=store, name=name)
        messages.success(request, f'Category "{name}" created.')
        return redirect("merchant-category-list")

    return render(request, "merchant/add_category.html", {"store": store})


@login_required
def dashboard(request):
    store = get_current_store(request)
    if not store:
        messages.info(request, "Create your first store to continue.")
        return redirect("merchant-profile")

    guard = _redirect_if_archived(request, store)
    if guard:
        return guard

    products_qs = store.products.all()
    orders_qs = store.orders.all().order_by("-created_at")

    product_count = products_qs.count()
    order_count = orders_qs.count()
    revenue = orders_qs.aggregate(total=Sum("total"))["total"] or Decimal("0.00")
    recent_orders = list(orders_qs[:10])

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
def reports(request):
    store = get_current_store(request)
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


@login_required
def order_list(request):
    store = get_current_store(request)
    if not store:
        messages.info(request, "Create your store to view orders.")
        return redirect("merchant-profile")

    guard = _redirect_if_archived(request, store)
    if guard:
        return guard

    orders = (
        store.orders
        .prefetch_related("items")
        .all()
        .order_by("-created_at")
    )

    total_orders = orders.count()
    paid_orders = orders.filter(status__in=["paid", "completed"]).count()
    pending_orders = orders.filter(status="pending").count()
    total_revenue = orders.filter(status__in=["paid", "completed"]).aggregate(
        total=Sum("total")
    )["total"] or Decimal("0.00")

    context = {
        "store": store,
        "orders": orders,
        "page_obj": None,
        "total_orders": total_orders,
        "paid_orders": paid_orders,
        "pending_orders": pending_orders,
        "total_revenue": total_revenue,
    }

    return render(request, "merchant/orders.html", context)


@login_required
def order_detail(request, order_id: int):
    store = get_current_store(request)
    if not store:
        messages.info(request, "Create your store to view orders.")
        return redirect("merchant-profile")

    order = get_object_or_404(
        Order.objects.prefetch_related("items"),
        pk=order_id,
        store=store,
    )

    item_count = order.items.count()
    subtotal = Decimal("0.00")
    for it in order.items.all():
        try:
            subtotal += (it.unit_price or Decimal("0.00")) * int(it.quantity or 0)
        except Exception:
            pass

    allowed_statuses = ["pending", "paid", "shipped", "completed", "canceled", "refunded"]
    shipping_statuses = ["processing", "packed", "shipped", "out_for_delivery", "delivered", "returned"]

    context = {
        "store": store,
        "order": order,
        "item_count": item_count,
        "subtotal": subtotal,
        "allowed_statuses": allowed_statuses,
        "shipping_statuses": shipping_statuses,
    }

    return render(request, "merchant/order_detail.html", context)


@login_required
def order_update_status(request, order_id: int):
    if request.method != "POST":
        return redirect("order-detail", order_id=order_id)

    store = get_current_store(request)
    if not store:
        messages.info(request, "Create your store to view orders.")
        return redirect("merchant-profile")

    guard = _redirect_if_archived(request, store)
    if guard:
        return guard

    order = get_object_or_404(Order, pk=order_id, store=store)

    allowed_statuses = {"pending", "paid", "shipped", "completed", "canceled", "refunded"}
    new_status = (request.POST.get("status") or "").strip().lower()

    if new_status not in allowed_statuses:
        messages.error(request, "Invalid order status selected.")
        return redirect("order-detail", order_id=order.id)

    old_status = order.status
    if old_status == new_status:
        messages.info(request, f"Order #{order.id} is already marked as {new_status}.")
        return redirect("order-detail", order_id=order.id)

    order.status = new_status
    order.save(update_fields=["status"])

    messages.success(
        request,
        f"Order #{order.id} status updated from {old_status} to {new_status}."
    )
    return redirect("order-detail", order_id=order.id)


@login_required
def order_update_shipping(request, order_id: int):
    if request.method != "POST":
        return redirect("order-detail", order_id=order_id)

    store = get_current_store(request)
    if not store:
        messages.info(request, "Create your store to update shipping.")
        return redirect("merchant-profile")

    guard = _redirect_if_archived(request, store)
    if guard:
        return guard

    order = get_object_or_404(Order, pk=order_id, store=store)

    allowed_shipping_statuses = {
        "processing",
        "packed",
        "shipped",
        "out_for_delivery",
        "delivered",
        "returned",
    }

    shipping_status = (request.POST.get("shipping_status") or "").strip().lower()
    shipping_carrier = (request.POST.get("shipping_carrier") or "").strip()
    tracking_number = (request.POST.get("tracking_number") or "").strip()
    tracking_url = (request.POST.get("tracking_url") or "").strip()

    if shipping_status not in allowed_shipping_statuses:
        messages.error(request, "Invalid shipping status selected.")
        return redirect("order-detail", order_id=order.id)

    old_status = getattr(order, "shipping_status", "processing")

    order.shipping_status = shipping_status
    order.shipping_carrier = shipping_carrier
    order.tracking_number = tracking_number
    order.tracking_url = tracking_url

    if shipping_status == "shipped" and not order.shipped_at:
        order.shipped_at = timezone.now()

    if shipping_status == "delivered" and not order.delivered_at:
        order.delivered_at = timezone.now()

    order.save(
        update_fields=[
            "shipping_status",
            "shipping_carrier",
            "tracking_number",
            "tracking_url",
            "shipped_at",
            "delivered_at",
        ]
    )

    messages.success(
        request,
        f"Order #{order.id} shipping updated from {old_status} to {shipping_status}."
    )
    return redirect("order-detail", order_id=order.id)


@login_required
def merchant_store_archive(request):
    store = get_current_store(request)
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
    store = get_current_store(request)
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


from decimal import Decimal, InvalidOperation

@login_required
def add_product(request):
    store = get_current_store(request)
    if not store:
        messages.error(request, "Create your store first.")
        return redirect("merchant-profile")

    guard = _redirect_if_archived(request, store)
    if guard:
        return guard

    categories = store.categories.all().order_by("name")

    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        description = (request.POST.get("description") or "").strip()
        image = request.FILES.get("image")
        digital_file = request.FILES.get("digital_file")
        category_id = (request.POST.get("category") or "").strip()
        product_type = (request.POST.get("product_type") or "physical").strip().lower()

        if product_type not in {"physical", "digital"}:
            product_type = "physical"

        price_val = Decimal("0.00")
        price_raw = (request.POST.get("price") or "").strip()
        if price_raw:
            try:
                price_val = Decimal(price_raw)
            except (InvalidOperation, ValueError):
                messages.error(request, "Price must be a valid number.")
                return render(request, "merchant/add_product.html", {"categories": categories})

        if not name:
            messages.error(request, "Please provide a product name.")
            return render(request, "merchant/add_product.html", {"categories": categories})

        selected_category = None
        if category_id:
            try:
                selected_category = store.categories.get(pk=int(category_id))
            except (ValueError, StoreCategory.DoesNotExist):
                messages.error(request, "Invalid category selected.")
                return render(request, "merchant/add_product.html", {"categories": categories})

        track_inventory = request.POST.get("track_inventory") == "on"

        try:
            stock_quantity = int(request.POST.get("stock_quantity") or 0)
        except (TypeError, ValueError):
            stock_quantity = 0

        try:
            low_stock_threshold = int(request.POST.get("low_stock_threshold") or 5)
        except (TypeError, ValueError):
            low_stock_threshold = 5

        product = Product(
            store=store,
            name=name,
            category=selected_category,
            product_type=product_type,
            price=price_val,
            description=description,
            track_inventory=track_inventory,
            stock_quantity=max(0, stock_quantity),
            low_stock_threshold=max(0, low_stock_threshold),
        )

        if image:
            product.image = image

        if product_type == "digital" and digital_file:
            product.digital_file = digital_file

        product.save()
        messages.success(request, "Product created successfully.")
        return redirect("merchant-dashboard")

    return render(request, "merchant/add_product.html", {"categories": categories})

@login_required
def edit_product(request, product_id: int):
    store = get_current_store(request)
    if not store:
        messages.error(request, "Create your store first.")
        return redirect("merchant-profile")

    guard = _redirect_if_archived(request, store)
    if guard:
        return guard

    product = get_object_or_404(Product, pk=product_id, store=store)
    categories = store.categories.all().order_by("name")

    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        description = (request.POST.get("description") or "").strip()
        image = request.FILES.get("image")
        digital_file = request.FILES.get("digital_file")
        category_id = (request.POST.get("category") or "").strip()
        product_type = (request.POST.get("product_type") or "physical").strip()

        if product_type not in {"physical", "digital"}:
            product_type = "physical"

        price_raw = (request.POST.get("price") or "").strip()
        if price_raw:
            try:
                price_val = Decimal(price_raw)
            except (InvalidOperation, ValueError):
                messages.error(request, "Price must be a valid number.")
                return render(
                    request,
                    "merchant/edit_product.html",
                    {"product": product, "categories": categories},
                )
        else:
            price_val = None

        if not name:
            messages.error(request, "Please provide a product name.")
            return render(
                request,
                "merchant/edit_product.html",
                {"product": product, "categories": categories},
            )

        selected_category = None
        if category_id:
            try:
                selected_category = store.categories.get(pk=int(category_id))
            except (ValueError, StoreCategory.DoesNotExist):
                messages.error(request, "Invalid category selected.")
                return render(
                    request,
                    "merchant/edit_product.html",
                    {"product": product, "categories": categories},
                )

        product.name = name
        product.product_type = product_type
        product.category = selected_category

        if hasattr(Product, "description"):
            product.description = description or ""
        if hasattr(Product, "price") and price_val is not None:
            product.price = price_val
        if hasattr(Product, "image") and image:
            product.image = image
        if hasattr(Product, "digital_file") and digital_file and product_type == "digital":
            product.digital_file = digital_file

        if hasattr(Product, "track_inventory"):
            product.track_inventory = request.POST.get("track_inventory") == "on"

        if hasattr(Product, "stock_quantity"):
            try:
                product.stock_quantity = max(0, int(request.POST.get("stock_quantity") or 0))
            except (TypeError, ValueError):
                product.stock_quantity = product.stock_quantity or 0

        if hasattr(Product, "low_stock_threshold"):
            try:
                product.low_stock_threshold = max(0, int(request.POST.get("low_stock_threshold") or 5))
            except (TypeError, ValueError):
                product.low_stock_threshold = product.low_stock_threshold or 5

        product.save()
        messages.success(request, "Product updated.")
        return redirect("merchant-dashboard")

    return render(
        request,
        "merchant/edit_product.html",
        {"product": product, "categories": categories},
    )


@login_required
def delete_product(request, product_id: int):
    store = (
        request.user.stores
        .filter(is_archived=False)
        .order_by("created_at")
        .first()
    )

    if not store:
        messages.error(request, "Create your store first.")
        return redirect("merchant-profile")

    guard = _redirect_if_archived(request, store)
    if guard:
        return guard

    product = get_object_or_404(
        Product,
        pk=product_id,
        store=store,
    )

    if request.method == "POST":
        name = product.name
        product.delete()
        messages.success(request, f'Deleted “{name}”.')
        return redirect("merchant-dashboard")

    return render(
        request,
        "merchant/confirm_delete.html",
        {
            "product": product,
            "store": store,
        },
    )

@login_required
def reports_export(request):
    store = get_current_store(request)
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


@login_required
def payment_settings(request):
    store = get_current_store(request)
    if not store:
        messages.error(request, "Create your store first.")
        return redirect("merchant-profile")

    ensure_default_payment_methods(store)

    methods = store.payment_methods.all().order_by("-is_default", "provider")
    return render(request, "merchant/payment_settings.html", {"store": store, "methods": methods})


@login_required
def payment_method_create(request):
    store = get_current_store(request)
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
    store = get_current_store(request)
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
    store = get_current_store(request)
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
    store = get_current_store(request)
    if not store:
        messages.error(request, "Create your store first.")
        return redirect("merchant-profile")

    ensure_default_payment_methods(store)

    pm = (
        store.payment_methods.filter(is_active=True, is_default=True).first()
        or store.payment_methods.filter(is_active=True).first()
    )
    if not pm:
        messages.error(request, "No active payment method. Add one in Payment Settings.")
        return redirect("merchant-payment-settings")

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


PLAN_PRICES = {
    "starter": 900,
    "pro": 2900,
    "elite": 7900,
}


@login_required
def plan_pricing(request):
    store = get_current_store(request)
    if not store:
        messages.info(request, "Create your store to continue.")
        return redirect("merchant-profile")

    ensure_default_payment_methods(store)

    methods = list(store.payment_methods.filter(is_active=True).order_by("-is_default", "provider"))
    return render(request, "merchant/plans.html", {"store": store, "methods": methods})


@login_required
def plan_checkout(request, plan_slug: str):
    plan = (plan_slug or "").lower()
    if plan not in PLAN_PRICES:
        messages.error(request, "Unknown plan.")
        return redirect("merchant-plans")

    store = get_current_store(request)
    if not store:
        messages.info(request, "Create your store to continue.")
        return redirect("merchant-profile")

    ensure_default_payment_methods(store)

    provider = (request.GET.get("provider") or "").lower()

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

    adapter = build_adapter(
        pm.provider,
        credentials=pm.credentials,
        success_url=success_url,
        cancel_url=cancel_url,
    )
    result = adapter.start_checkout(
        amount_cents=amount_cents,
        currency=currency,
        metadata={"store_id": store.id, "plan": plan, "purchase_type": "subscription"},
    )
    return redirect(result["redirect_url"])


@login_required
def plan_checkout_success(request):
    store = get_current_store(request)
    if not store:
        messages.info(request, "Create your store to continue.")
        return redirect("merchant-profile")

    plan = (request.GET.get("plan") or "").lower()
    if plan not in PLAN_PRICES:
        messages.warning(request, "Payment approved (demo), but plan was unknown.")
        return redirect("merchant-dashboard")

    store.plan = plan
    store.save(update_fields=["plan"])
    messages.success(request, f"Your plan has been updated to {plan.title()}.")
    return redirect("merchant-dashboard")


@login_required
def plan_checkout_cancel(request):
    messages.warning(request, "Plan checkout canceled.")
    return redirect("merchant-plans")


@staff_required
def admin_store_list(request):
    q = (request.GET.get("q") or "").strip()
    zone_slug = (request.GET.get("zone") or "").strip()
    plan = (request.GET.get("plan") or "").strip()
    status = (request.GET.get("status") or "").strip()

    stores = Store.objects.select_related("owner", "zone").prefetch_related("products", "orders")

    if q:
        stores = stores.filter(
            models.Q(store_name__icontains=q)
            | models.Q(owner__username__icontains=q)
            | models.Q(owner__email__icontains=q)
            | models.Q(contact_person__icontains=q)
            | models.Q(contact_email__icontains=q)
            | models.Q(contact_phone__icontains=q)
            | models.Q(zone__name__icontains=q)
        )

    if zone_slug:
        stores = stores.filter(zone__slug=zone_slug)

    if plan:
        stores = stores.filter(plan=plan)

    if status == "live":
        stores = stores.filter(is_public=True, is_archived=False)
    elif status == "archived":
        stores = stores.filter(is_archived=True)
    elif status == "hidden":
        stores = stores.filter(is_public=False, is_archived=False)
    elif status == "featured":
        stores = stores.filter(is_featured=True, is_archived=False)

    stores = stores.order_by("-created_at")

    zones = MallZone.objects.filter(is_active=True).order_by("sort_order", "name")

    stats = {
        "total": Store.objects.count(),
        "live": Store.objects.filter(is_public=True, is_archived=False).count(),
        "archived": Store.objects.filter(is_archived=True).count(),
        "featured": Store.objects.filter(is_featured=True, is_archived=False).count(),
    }

    context = {
        "stores": stores,
        "zones": zones,
        "q": q,
        "selected_zone": zone_slug,
        "selected_plan": plan,
        "selected_status": status,
        "stats": stats,
    }
    return render(request, "merchant/stores_admin.html", context)


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


def _json(request):
    try:
        return json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return None


@csrf_exempt
@csrf_exempt
def webhook_stripe(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=settings.STRIPE_WEBHOOK_SECRET,
        )
    except ValueError:
        return HttpResponseBadRequest("Invalid payload")
    except stripe.error.SignatureVerificationError:
        return HttpResponseBadRequest("Invalid signature")

    try:
        event_type = event["type"]
    except Exception:
        event_type = ""

    try:
        data_object = event["data"]["object"]
    except Exception:
        data_object = None

    if event_type in {"checkout.session.completed", "checkout.session.async_payment_succeeded"} and data_object:
        _mark_order_paid_from_checkout_session(data_object)

    return HttpResponse(status=200)


@csrf_exempt
def webhook_paypal(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    event = _json(request)
    if event is None:
        return HttpResponseBadRequest("Invalid JSON")
    return HttpResponse(status=200)

@csrf_exempt
def webhook_coinbase(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    payload = request.body
    signature = request.META.get("HTTP_X_CC_WEBHOOK_SIGNATURE", "")
    webhook_secret = getattr(settings, "COINBASE_COMMERCE_WEBHOOK_SECRET", "")

    if webhook_secret:
        expected = hmac.new(
            webhook_secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected, signature):
            return HttpResponseBadRequest("Invalid Coinbase signature")

    event = _json(request)
    if event is None:
        return HttpResponseBadRequest("Invalid JSON")

    event_obj = event.get("event", event)
    event_type = event_obj.get("type", "")
    data = event_obj.get("data", {}) or {}
    metadata = data.get("metadata", {}) or {}

    order_id = metadata.get("order_id")
    if not order_id:
        return HttpResponse(status=200)

    try:
        order = Order.objects.select_related("store").prefetch_related("items").get(pk=int(order_id))
    except (ValueError, TypeError, Order.DoesNotExist):
        return HttpResponse(status=200)

    if event_type in {"charge:confirmed", "charge:resolved"}:
        if order.status != "paid":
            order.status = "paid"
            order.save(update_fields=["status"])

            customer_name = (
                getattr(order, "customer_name", "")
                or metadata.get("customer_name", "")
            )
            customer_email = (
                getattr(order, "customer_email", "")
                or metadata.get("customer_email", "")
            )

            send_order_confirmation_emails(
                order=order,
                customer_name=customer_name,
                customer_email=customer_email,
            )

    elif event_type in {"charge:failed", "charge:expired"}:
        if order.status == "pending":
            order.status = "canceled"
            order.save(update_fields=["status"])

    return HttpResponse(status=200)

@staff_required
def operations_center(request):
    users_count = 0
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        users_count = User.objects.count()
    except Exception:
        users_count = 0

    stats = {
        "users": users_count,
        "zones": MallZone.objects.count(),
        "stores": MerchantStore.objects.count(),
        "live_stores": MerchantStore.objects.filter(is_public=True, is_archived=False).count(),
        "products": Product.objects.count(),
        "orders": Order.objects.count(),
        "pending_orders": Order.objects.filter(status="pending").count(),
        "paid_orders": Order.objects.filter(status__in=["paid", "completed"]).count(),
        "pending_shipments": Order.objects.filter(
            status__in=["paid", "completed"],
            shipping_status__in=["processing", "packed", "shipped", "out_for_delivery"],
        ).count(),
        "low_stock": Product.objects.filter(
            track_inventory=True,
            stock_quantity__lte=models.F("low_stock_threshold"),
        ).count(),
        "revenue": Order.objects.filter(status__in=["paid", "completed"]).aggregate(
            total=Sum("total")
        )["total"] or Decimal("0.00"),
    }

    recent_orders = Order.objects.select_related("store").order_by("-created_at")[:10]
    recent_stores = MerchantStore.objects.select_related("owner").order_by("-created_at")[:10]

    return render(
        request,
        "merchant/operations/dashboard.html",
        {
            "stats": stats,
            "recent_orders": recent_orders,
            "recent_stores": recent_stores,
        },
    )

