"""
MajicMall Megaverse interior theme engine.

This module is the single source of truth for merchant-store interior
themes. Themes are visual experiences only. Customer-facing pages must
never display merchant subscription plans or membership classifications.
"""

INTERIOR_THEMES = {
    "signature": {
        "slug": "signature",
        "name": "MajicMall Signature Showroom",
        "icon": "✨",
        "description": (
            "A versatile luxury showroom with black glass, warm gold "
            "lighting, elegant displays, and a grand central welcome area."
        ),
        "family": "universal",
    },
    "fashion_boutique": {
        "slug": "fashion_boutique",
        "name": "Luxury Fashion Boutique",
        "icon": "👗",
        "description": (
            "A polished boutique environment with illuminated display "
            "walls, elegant racks, mirrors, and center presentation tables."
        ),
        "family": "fashion",
    },
    "tech_gallery": {
        "slug": "tech_gallery",
        "name": "Black Glass Tech Gallery",
        "icon": "💻",
        "description": (
            "A modern technology showroom with black glass, precision "
            "lighting, demonstration islands, and digital display walls."
        ),
        "family": "tech",
    },
    "food_hall": {
        "slug": "food_hall",
        "name": "Majestic Food Hall",
        "icon": "🍽️",
        "description": (
            "A warm premium restaurant and food-service environment with "
            "a welcome counter, menu displays, and comfortable hospitality."
        ),
        "family": "food",
    },
    "music_lounge": {
        "slug": "music_lounge",
        "name": "Music Studio Lounge",
        "icon": "🎵",
        "description": (
            "A sophisticated music lounge with studio lighting, listening "
            "areas, record displays, instruments, and performance energy."
        ),
        "family": "music",
    },
    "automotive_gallery": {
        "slug": "automotive_gallery",
        "name": "Luxury Automotive Gallery",
        "icon": "🚘",
        "description": (
            "A dramatic automotive showroom with display platforms, "
            "architectural lighting, polished floors, and performance style."
        ),
        "family": "automotive",
    },
    "creator_studio": {
        "slug": "creator_studio",
        "name": "Creator Gallery Studio",
        "icon": "🎨",
        "description": (
            "A flexible gallery and creative studio for art, merchandise, "
            "media, books, photography, and original experiences."
        ),
        "family": "creator",
    },
    "sports_arena": {
        "slug": "sports_arena",
        "name": "Championship Sports Shop",
        "icon": "🏆",
        "description": (
            "An energetic arena-inspired retail environment with trophy "
            "displays, team-style presentation walls, and bold lighting."
        ),
        "family": "sports",
    },
    "theater_lobby": {
        "slug": "theater_lobby",
        "name": "Premiere Theater Lobby",
        "icon": "🎭",
        "description": (
            "A cinematic lobby with velvet accents, premiere lighting, "
            "poster displays, red-carpet details, and concession elegance."
        ),
        "family": "theater",
    },
    "kids_adventure": {
        "slug": "kids_adventure",
        "name": "Kids Adventure Shop",
        "icon": "🎈",
        "description": (
            "A bright, playful, family-friendly environment with colorful "
            "displays, imagination stations, and joyful movement."
        ),
        "family": "kids",
    },
    "travel_lounge": {
        "slug": "travel_lounge",
        "name": "World Travel Lounge",
        "icon": "✈️",
        "description": (
            "An elegant travel lounge with destination displays, digital "
            "journey walls, concierge areas, and resort-inspired styling."
        ),
        "family": "travel",
    },
}


DEFAULT_INTERIOR_THEME = "signature"


ZONE_THEME_KEYWORDS = (
    (("fashion", "beauty", "lifestyle"), "fashion_boutique"),
    (("tech", "technology", "electronics"), "tech_gallery"),
    (("food", "restaurant", "dining", "florist"), "food_hall"),
    (("music", "audio", "record"), "music_lounge"),
    (("automotive", "vehicle", "car"), "automotive_gallery"),
    (("creator", "artist", "reader", "book", "non profit"), "creator_studio"),
    (("sports", "fitness"), "sports_arena"),
    (("theater", "movie", "film", "entertainment"), "theater_lobby"),
    (("kids", "children", "family"), "kids_adventure"),
    (("travel", "vacation", "tourism"), "travel_lounge"),
)


def normalize_interior_theme(theme_slug):
    normalized = str(theme_slug or "").strip().lower()

    if normalized not in INTERIOR_THEMES:
        normalized = DEFAULT_INTERIOR_THEME

    return normalized


def get_interior_theme(theme_slug):
    normalized = normalize_interior_theme(theme_slug)
    return INTERIOR_THEMES[normalized].copy()


def recommend_interior_theme(store):
    """
    Recommend a theme from the store's Zone and category.

    This does not overwrite the merchant's selected theme.
    """
    zone = getattr(store, "zone", None)

    searchable_text = " ".join(
        [
            getattr(zone, "name", "") or "",
            getattr(zone, "slug", "") or "",
            getattr(store, "category", "") or "",
        ]
    ).lower()

    for keywords, theme_slug in ZONE_THEME_KEYWORDS:
        if any(keyword in searchable_text for keyword in keywords):
            return get_interior_theme(theme_slug)

    return get_interior_theme(DEFAULT_INTERIOR_THEME)


def available_interior_themes():
    return [
        theme.copy()
        for theme in INTERIOR_THEMES.values()
    ]
