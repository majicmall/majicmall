from decimal import Decimal, ROUND_HALF_UP
from django import template

register = template.Library()

def _to_decimal(val):
    try:
        return Decimal(str(val))
    except Exception:
        return Decimal("0.00")

@register.filter
def currency(value):
    """Format a number as $X.YY"""
    d = _to_decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"${d}"

@register.filter
def mul(a, b):
    """Multiply in template: {{ qty|mul:unit_price|currency }}"""
    return _to_decimal(a) * _to_decimal(b)

@register.filter
def line_total(item):
    """Compute OrderItem line total: {{ item|line_total|currency }}"""
    return _to_decimal(getattr(item, "quantity", 0)) * _to_decimal(getattr(item, "unit_price", 0))
