"""
MajicMall Megaverse Merchant Success Plan engine.

This module is the single source of truth for:

- Success Plan names
- Monthly pricing presentation
- Included Zone Storefront allocations
- Legacy plan compatibility
- Current storefront usage
- Remaining storefront allocation

It does not process payments or enforce storefront creation yet.
"""

SUCCESS_PLANS = {
    "vision": {
        "slug": "vision",
        "name": "Vision",
        "icon": "🌟",
        "monthly_price": 19,
        "included_storefronts": 1,
        "accent": "vision",
        "summary": (
            "Launch and establish your business inside the "
            "MajicMall Megaverse."
        ),
    },
    "pro": {
        "slug": "pro",
        "name": "Pro",
        "icon": "🚀",
        "monthly_price": 49,
        "included_storefronts": 3,
        "accent": "pro",
        "summary": (
            "Expand into more zones and accelerate your business growth."
        ),
    },
    "elite": {
        "slug": "elite",
        "name": "Elite",
        "icon": "💎",
        "monthly_price": 99,
        "included_storefronts": 6,
        "accent": "elite",
        "summary": (
            "Premium visibility, promotion, media, and advanced analytics."
        ),
    },
    "enterprise": {
        "slug": "enterprise",
        "name": "Enterprise",
        "icon": "🏢",
        "monthly_price": 199,
        "included_storefronts": 12,
        "accent": "enterprise",
        "summary": (
            "Advanced multi-brand, multi-zone, and multi-team operations."
        ),
    },
    "majestic": {
        "slug": "majestic",
        "name": "Majestic",
        "icon": "👑",
        "monthly_price": 499,
        "included_storefronts": None,
        "storefront_label": "Custom high-volume allocation",
        "accent": "majestic",
        "summary": (
            "The complete MajesticMall Megaverse merchant experience."
        ),
    },
    "foundation": {
        "slug": "foundation",
        "name": "Foundation Merchant",
        "icon": "🏅",
        "monthly_price": 0,
        "included_storefronts": 1,
        "accent": "foundation",
        "summary": (
            "Original merchant recognition with preferred benefits."
        ),
    },
}


LEGACY_PLAN_ALIASES = {
    "starter": "vision",
    "basic": "vision",
}


DEFAULT_PLAN_SLUG = "vision"


def normalize_plan_slug(plan_slug):
    """
    Convert stored and legacy plan names into a supported plan slug.
    """
    normalized = str(plan_slug or "").strip().lower()
    normalized = LEGACY_PLAN_ALIASES.get(normalized, normalized)

    if normalized not in SUCCESS_PLANS:
        normalized = DEFAULT_PLAN_SLUG

    return normalized


def get_success_plan(plan_slug):
    """
    Return an independent copy of the requested Success Plan.
    """
    normalized = normalize_plan_slug(plan_slug)
    return SUCCESS_PLANS[normalized].copy()


def get_storefront_usage(store):
    """
    Return account-level Zone Storefront usage for the store owner.

    Archived storefronts do not consume the active allocation.

    The MerchantStore model is imported inside this function to avoid
    circular-import problems when Django loads models and template tags.
    """
    from merchant.models import MerchantStore

    if store is None:
        return None

    plan = get_success_plan(getattr(store, "plan", None))
    owner = getattr(store, "owner", None)

    if owner is None:
        used_storefronts = 0
    else:
        used_storefronts = MerchantStore.objects.filter(
            owner=owner,
            is_archived=False,
        ).count()

    included_storefronts = plan["included_storefronts"]

    if included_storefronts is None:
        remaining_storefronts = None
        can_create_storefront = True
        allocation_label = plan.get(
            "storefront_label",
            "Custom allocation",
        )
    else:
        remaining_storefronts = max(
            included_storefronts - used_storefronts,
            0,
        )

        can_create_storefront = remaining_storefronts > 0
        allocation_label = f"{included_storefronts} included"

    plan.update(
        {
            "used_storefronts": used_storefronts,
            "remaining_storefronts": remaining_storefronts,
            "can_create_storefront": can_create_storefront,
            "allocation_label": allocation_label,
            "additional_storefront_price": 15,
        }
    )

    return plan
