from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from merchant.models import MerchantStore

from .pickup_forms import MerchantPickupAddressForm
from .pickup_models import MerchantPickupAddress


SESSION_STORE_KEY = "merchant_store_id"


def _merchant_store_for_request(request):
    stores = (
        MerchantStore.objects
        .filter(
            owner=request.user,
            is_archived=False,
        )
        .order_by("created_at", "id")
    )

    requested_store_id = (
        request.GET.get("store")
        or request.POST.get("store")
        or request.session.get(SESSION_STORE_KEY)
    )

    store = None

    if requested_store_id:
        try:
            store = stores.get(pk=int(requested_store_id))
        except (
            TypeError,
            ValueError,
            MerchantStore.DoesNotExist,
        ):
            store = None

    if store is None:
        store = stores.first()

    if store:
        request.session[SESSION_STORE_KEY] = store.id
        request.session.modified = True

    return store, stores


@login_required
def merchant_pickup_address(request):
    store, stores = _merchant_store_for_request(request)

    if store is None:
        messages.info(
            request,
            "Create your merchant storefront before adding a pickup address.",
        )
        return redirect("merchant-profile")

    pickup_address, _created = (
        MerchantPickupAddress.objects.get_or_create(
            store=store,
            defaults={
                "postal_code": store.business_zip or "",
            },
        )
    )

    if request.method == "POST":
        form = MerchantPickupAddressForm(
            request.POST,
            instance=pickup_address,
        )

        if form.is_valid():
            pickup_address = form.save(commit=False)

            # A saved merchant address is considered merchant-confirmed.
            pickup_address.is_verified = True
            pickup_address.save()

            if (
                pickup_address.postal_code
                and store.business_zip != pickup_address.postal_code
            ):
                store.business_zip = pickup_address.postal_code
                store.save(update_fields=["business_zip"])

            messages.success(
                request,
                (
                    "Your exact merchant pickup location has been saved. "
                    "Drivers will now receive street-level navigation."
                ),
            )

            return redirect(
                f"/delivery/merchant-pickup-address/?store={store.id}"
            )
    else:
        form = MerchantPickupAddressForm(
            instance=pickup_address,
        )

    return render(
        request,
        "delivery/merchant_pickup_address.html",
        {
            "store": store,
            "stores": stores,
            "pickup_address": pickup_address,
            "form": form,
        },
    )
