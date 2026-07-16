from django import template

from merchant.interior_themes import (
    get_interior_theme,
    recommend_interior_theme,
)


register = template.Library()


@register.simple_tag
def merchant_interior_theme(store):
    if not store:
        return get_interior_theme("signature")

    return get_interior_theme(
        getattr(store, "interior_theme", "signature")
    )


@register.simple_tag
def recommended_interior_theme(store):
    if not store:
        return get_interior_theme("signature")

    return recommend_interior_theme(store)
