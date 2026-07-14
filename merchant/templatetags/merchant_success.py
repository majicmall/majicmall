from django import template

from merchant.success_plans import get_storefront_usage


register = template.Library()


@register.simple_tag
def merchant_success_summary(store):
    """
    Load the current merchant Success Plan summary.

    Template usage:

        {% merchant_success_summary store as success_plan %}
    """
    if not store:
        return None

    return get_storefront_usage(store)
