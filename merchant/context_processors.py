from .models import MerchantStore

Store = MerchantStore


def merchant_nav(request):
    if not request.user.is_authenticated:
        return {}

    stores = Store.objects.filter(owner=request.user, is_archived=False).order_by("created_at")

    current_store = None
    sid = request.session.get("active_store_id")
    if sid:
        try:
            current_store = stores.get(pk=int(sid))
        except Exception:
            current_store = stores.first()
    else:
        current_store = stores.first()

    return {
        "nav_stores": stores,
        "nav_current_store": current_store,
    }