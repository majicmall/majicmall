import ast
import os
import secrets
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import ForeignKey, OneToOneField
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.text import slugify

from .models import MerchantStore
from .payments.adapters import PaymentAdapterError, build_adapter
from .success_plans import get_success_plan


SUPPORTED_PROVIDERS = {
    "stripe": "Stripe",
    "paypal": "PayPal",
    "coinbase": "Coinbase Commerce",
    "square": "Square",
}


def _extract_plan_slug(value):
    """
    Accept a slug, a plan dictionary, or a stale string representation
    of a dictionary and return one clean Success Plan slug.
    """
    if isinstance(value, dict):
        value = value.get("slug")

    if isinstance(value, str):
        cleaned = value.strip()

        # Repair stale session/URL values such as:
        # "{'slug': 'pro', 'name': 'Pro', ...}"
        if cleaned.startswith("{") and cleaned.endswith("}"):
            try:
                parsed = ast.literal_eval(cleaned)
            except (ValueError, SyntaxError):
                parsed = None

            if isinstance(parsed, dict):
                cleaned = str(parsed.get("slug", "")).strip()

        value = cleaned

    return str(value or "vision").strip().lower()


def _plan_details(value):
    requested_slug = _extract_plan_slug(value)
    details = get_success_plan(requested_slug)

    if not isinstance(details, dict):
        details = get_success_plan("vision")

    if not isinstance(details, dict):
        raise RuntimeError(
            "Merchant Success Plan configuration did not return a plan dictionary."
        )

    return details


def _normalized_plan(value):
    return str(_plan_details(value).get("slug") or "vision").lower()


def _plan_price_dollars(value):
    details = _plan_details(value)

    try:
        return Decimal(str(details.get("monthly_price", 0)))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0.00")


def _plan_price_cents(value):
    return int(_plan_price_dollars(value) * 100)

def _selected_plan(request):
    return _normalized_plan(
        request.GET.get("plan")
        or request.POST.get("plan")
        or request.session.get("selected_merchant_success_plan")
    )


def _unique_username(User, email):
    base = slugify(email.split("@")[0])[:120] or "merchant"
    candidate = base
    counter = 2

    username_field = getattr(User, "USERNAME_FIELD", "username")

    while User._default_manager.filter(
        **{f"{username_field}__iexact": candidate}
    ).exists():
        candidate = f"{base}{counter}"
        counter += 1

    return candidate


def _provider_credentials(provider):
    credentials = {
        "stripe": {
            "secret_key": getattr(settings, "STRIPE_SECRET_KEY", "")
            or os.getenv("STRIPE_SECRET_KEY", ""),
            "publishable_key": getattr(settings, "STRIPE_PUBLISHABLE_KEY", "")
            or os.getenv("STRIPE_PUBLISHABLE_KEY", ""),
        },
        "paypal": {
            "client_id": getattr(settings, "PAYPAL_CLIENT_ID", "")
            or os.getenv("PAYPAL_CLIENT_ID", ""),
            "client_secret": getattr(settings, "PAYPAL_CLIENT_SECRET", "")
            or os.getenv("PAYPAL_CLIENT_SECRET", ""),
            "mode": getattr(settings, "PAYPAL_MODE", "")
            or os.getenv("PAYPAL_MODE", "sandbox"),
        },
        "coinbase": {
            "api_key": getattr(settings, "COINBASE_COMMERCE_API_KEY", "")
            or os.getenv("COINBASE_COMMERCE_API_KEY", ""),
            "shared_secret": getattr(
                settings,
                "COINBASE_COMMERCE_WEBHOOK_SECRET",
                "",
            )
            or os.getenv("COINBASE_COMMERCE_WEBHOOK_SECRET", ""),
        },
        "square": {
            "access_token": getattr(settings, "SQUARE_ACCESS_TOKEN", "")
            or os.getenv("SQUARE_ACCESS_TOKEN", ""),
            "location_id": getattr(settings, "SQUARE_LOCATION_ID", "")
            or os.getenv("SQUARE_LOCATION_ID", ""),
            "environment": getattr(settings, "SQUARE_ENVIRONMENT", "")
            or os.getenv("SQUARE_ENVIRONMENT", "sandbox"),
        },
    }

    return credentials.get(provider, {})


def _required_store_defaults(user, pending, plan):
    """
    Build MerchantStore kwargs from the real model instead of hard-coding
    every field name. Known MajicMall Megaverse fields receive meaningful
    values; other required text fields receive safe temporary values.
    """
    business_name = pending.get("business_name") or "My MajicMall Store"
    category_name = pending.get("business_category") or "General"
    phone = pending.get("phone") or ""

    kwargs = {}

    for field in MerchantStore._meta.concrete_fields:
        if field.primary_key or field.auto_created:
            continue

        name = field.name

        if isinstance(field, (ForeignKey, OneToOneField)):
            related_model = field.remote_field.model

            if related_model == get_user_model():
                kwargs[name] = user
                continue

            if field.null:
                continue

            related_object = related_model._default_manager.first()
            if related_object is not None:
                kwargs[name] = related_object

            continue

        if name in {"name", "store_name", "business_name", "title"}:
            kwargs[name] = business_name
        elif name == "slug":
            root = slugify(business_name)[:45] or "merchant-store"
            slug = root
            number = 2

            while MerchantStore.objects.filter(slug=slug).exists():
                slug = f"{root}-{number}"
                number += 1

            kwargs[name] = slug
        elif name == "plan":
            kwargs[name] = plan
        elif name in {"category", "business_category", "store_category"}:
            if not field.is_relation:
                kwargs[name] = category_name
        elif name in {"phone", "phone_number", "business_phone"}:
            kwargs[name] = phone
        elif name in {"description", "slogan"}:
            kwargs[name] = ""
        elif name == "is_public":
            kwargs[name] = False
        elif name == "is_archived":
            kwargs[name] = False
        elif not field.null and not field.has_default():
            internal_type = field.get_internal_type()

            if internal_type in {
                "CharField",
                "TextField",
                "EmailField",
                "URLField",
            }:
                kwargs[name] = ""
            elif internal_type == "BooleanField":
                kwargs[name] = False
            elif internal_type in {
                "IntegerField",
                "PositiveIntegerField",
                "SmallIntegerField",
                "PositiveSmallIntegerField",
            }:
                kwargs[name] = 0

    return kwargs


def _find_existing_store(user):
    for field in MerchantStore._meta.fields:
        if (
            isinstance(field, (ForeignKey, OneToOneField))
            and field.remote_field.model == get_user_model()
        ):
            store = MerchantStore.objects.filter(**{field.name: user}).first()
            if store:
                return store

    return None


def _create_store(user, pending, plan):
    existing = _find_existing_store(user)

    if existing:
        if hasattr(existing, "plan"):
            existing.plan = plan
            existing.save(update_fields=["plan"])

        return existing

    kwargs = _required_store_defaults(user, pending, plan)
    return MerchantStore.objects.create(**kwargs)


def build_empire(request):
    plan = _selected_plan(request)
    request.session["selected_merchant_success_plan"] = plan
    request.session.modified = True

    if request.user.is_authenticated:
        return redirect("merchant-empire-checkout")

    if request.method == "POST":
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")
        password_confirm = request.POST.get("password_confirm", "")
        business_name = request.POST.get("business_name", "").strip()
        business_category = request.POST.get(
            "business_category",
            "",
        ).strip()
        phone = request.POST.get("phone", "").strip()
        agreement = request.POST.get("agreement")

        errors = []

        if not first_name:
            errors.append("Enter your first name.")
        if not last_name:
            errors.append("Enter your last name.")
        if not email:
            errors.append("Enter your email address.")
        if not business_name:
            errors.append("Enter your business name.")
        if len(password) < 8:
            errors.append("Password must contain at least 8 characters.")
        if password != password_confirm:
            errors.append("The passwords do not match.")
        if not agreement:
            errors.append("Accept the Merchant Agreement to continue.")

        User = get_user_model()

        email_field = None

        try:
            email_field = User._meta.get_field("email")
        except Exception:
            pass

        if email_field and User._default_manager.filter(
            email__iexact=email
        ).exists():
            errors.append(
                "An account already exists with this email. Please sign in."
            )

        if errors:
            for error in errors:
                messages.error(request, error)

            return render(
                request,
                "merchant/build_empire.html",
                {
                    "plan": plan,
                    "plan_price": _plan_price_dollars(plan),
                },
            )

        username_field = getattr(User, "USERNAME_FIELD", "username")
        create_values = {}

        if username_field == "email":
            create_values["email"] = email
        else:
            create_values[username_field] = _unique_username(User, email)

            if email_field:
                create_values["email"] = email

        field_names = {field.name for field in User._meta.fields}

        if "first_name" in field_names:
            create_values["first_name"] = first_name

        if "last_name" in field_names:
            create_values["last_name"] = last_name

        with transaction.atomic():
            user = User._default_manager.create_user(
                password=password,
                **create_values,
            )

        request.session["pending_merchant_empire"] = {
            "token": secrets.token_urlsafe(24),
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "business_name": business_name,
            "business_category": business_category,
            "phone": phone,
            "plan": plan,
        }

        request.session.modified = True

        login(
            request,
            user,
            backend="django.contrib.auth.backends.ModelBackend",
        )

        messages.success(
            request,
            "Your MajicMall Megaverse account has been created.",
        )

        return redirect("merchant-empire-checkout")

    return render(
        request,
        "merchant/build_empire.html",
        {
            "plan": plan,
            "plan_price": _plan_price_dollars(plan),
        },
    )


@login_required
def empire_checkout(request):
    pending = request.session.get("pending_merchant_empire") or {}
    plan = _normalized_plan(
        pending.get("plan")
        or request.session.get("selected_merchant_success_plan")
    )

    if request.method == "POST":
        provider = (request.POST.get("provider") or "").strip().lower()

        if provider not in SUPPORTED_PROVIDERS:
            messages.error(request, "Choose a payment method.")
            return redirect("merchant-empire-checkout")

        credentials = _provider_credentials(provider)

        success_url = request.build_absolute_uri(
            reverse("merchant-empire-success")
        )
        cancel_url = request.build_absolute_uri(
            reverse("merchant-empire-cancel")
        )

        success_url += f"?plan={plan}&provider={provider}"

        try:
            adapter = build_adapter(
                provider,
                credentials=credentials,
                success_url=success_url,
                cancel_url=cancel_url,
            )

            result = adapter.start_checkout(
                amount_cents=_plan_price_cents(plan),
                currency="usd",
                metadata={
                    "user_id": request.user.pk,
                    "plan": plan,
                    "purchase_type": "new_merchant_subscription",
                    "empire_token": pending.get("token", ""),
                },
            )

            redirect_url = result.get("redirect_url")

            if not redirect_url:
                raise PaymentAdapterError(
                    "The payment provider did not return a checkout URL."
                )

            request.session["merchant_checkout_provider"] = provider
            request.session.modified = True

            return redirect(redirect_url)

        except Exception as exc:
            messages.error(
                request,
                f"{SUPPORTED_PROVIDERS[provider]} checkout could not start: {exc}",
            )

    return render(
        request,
        "merchant/empire_checkout.html",
        {
            "plan": plan,
            "plan_price": _plan_price_dollars(plan),
            "providers": SUPPORTED_PROVIDERS,
            "pending": pending,
        },
    )


@login_required
def empire_checkout_success(request):
    pending = request.session.get("pending_merchant_empire") or {}
    plan = _normalized_plan(
        request.GET.get("plan")
        or pending.get("plan")
        or request.session.get("selected_merchant_success_plan")
    )

    try:
        with transaction.atomic():
            store = _create_store(request.user, pending, plan)
    except Exception as exc:
        messages.error(
            request,
            f"Payment returned successfully, but the store could not be created: {exc}",
        )
        return redirect("merchant-empire-checkout")

    request.session["new_merchant_store_id"] = store.pk
    request.session["new_merchant_plan"] = plan
    request.session.pop("pending_merchant_empire", None)
    request.session.modified = True

    return redirect("merchant-empire-welcome")


@login_required
def empire_checkout_cancel(request):
    messages.warning(
        request,
        "Your payment was canceled. Your account and selected plan were saved.",
    )
    return redirect("merchant-empire-checkout")


@login_required
def empire_welcome(request):
    plan = _normalized_plan(
        request.session.get("new_merchant_plan")
        or request.session.get("selected_merchant_success_plan")
    )

    store = None
    store_id = request.session.get("new_merchant_store_id")

    if store_id:
        store = MerchantStore.objects.filter(pk=store_id).first()

    if store is None:
        store = _find_existing_store(request.user)

    return render(
        request,
        "merchant/empire_welcome.html",
        {
            "store": store,
            "plan": plan,
        },
    )
