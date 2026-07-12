MERCHANT_SUCCESS_PLANS = {
    "vision": {
        "slug": "vision",
        "name": "Vision",
        "icon": "🌟",
        "price": 19,
        "storefronts": 1,
        "description": (
            "Launch your first professional Zone Storefront inside "
            "the MajicMall Megaverse."
        ),
        "highlights": [
            "1 Zone Storefront",
            "Full product catalog and secure checkout",
            "Fulfillment Center and order alerts",
            "Customer pickup workflow",
            "Merchant shipping support",
            "Local delivery eligibility",
        ],
    },
    "pro": {
        "slug": "pro",
        "name": "Pro",
        "icon": "🚀",
        "price": 49,
        "storefronts": 3,
        "description": (
            "Expand into additional zones and create professional "
            "promotional campaigns in minutes."
        ),
        "highlights": [
            "3 Zone Storefronts",
            "AI Store Manager access",
            "AI Marketing Director assistance",
            "Billboard and banner campaign tools",
            "Enhanced analytics",
            "Priority email support",
        ],
    },
    "elite": {
        "slug": "elite",
        "name": "Elite",
        "icon": "💎",
        "price": 99,
        "storefronts": 6,
        "description": (
            "Premium visibility, media, AI promotion, and multi-zone "
            "growth for ambitious brands."
        ),
        "highlights": [
            "6 Zone Storefronts",
            "Digital Billboard Advertising credits",
            "AI Brand Ambassador tools",
            "Advanced customer and sales analytics",
            "Branded Business Media Channel",
            "Branded video player and scheduled programming",
        ],
    },
    "enterprise": {
        "slug": "enterprise",
        "name": "Enterprise",
        "icon": "🏢",
        "price": 199,
        "storefronts": 12,
        "description": (
            "Multi-brand operations, advanced permissions, reporting, "
            "and concierge business support."
        ),
        "highlights": [
            "12 Zone Storefronts",
            "Multi-brand and department operations",
            "Advanced staff roles and permissions",
            "Executive reporting",
            "Expanded AI business team access",
            "Concierge onboarding",
        ],
    },
    "majestic": {
        "slug": "majestic",
        "name": "Majestic",
        "icon": "👑",
        "price": 499,
        "storefronts": None,
        "storefront_label": "Custom high-volume allocation",
        "description": (
            "The complete MajesticMall Megaverse merchant experience "
            "for visionary organizations and high-volume brands."
        ),
        "highlights": [
            "Custom multi-zone expansion",
            "Full available AI Executive Team access",
            "Premium homepage and directory visibility",
            "Priority Digital Billboard opportunities",
            "Premium Business Media services",
            "White-glove onboarding",
        ],
    },
    "foundation": {
        "slug": "foundation",
        "name": "Foundation Merchant",
        "icon": "🏅",
        "price": 0,
        "storefronts": 1,
        "description": (
            "Invitation-only recognition for qualifying original "
            "MajicMall Megaverse merchants."
        ),
        "highlights": [
            "1 complimentary Vision-level Zone Storefront for one year",
            "25% eligible lifetime active merchant discount",
            "Foundation Merchant recognition",
            "Discounted additional Zone Storefronts",
            "Early feature access",
            "Merchant community opportunities",
        ],
    },
}


DEFAULT_MERCHANT_SUCCESS_PLAN = "vision"


def get_merchant_success_plan(plan_slug):
    normalized_slug = (
        str(plan_slug or "")
        .strip()
        .lower()
    )

    if normalized_slug not in MERCHANT_SUCCESS_PLANS:
        normalized_slug = DEFAULT_MERCHANT_SUCCESS_PLAN

    return MERCHANT_SUCCESS_PLANS[normalized_slug].copy()
