from decimal import Decimal

from django import template

from majestian_economy.models import MajesticCoinSettings
from majestian_economy.services import EconomyEngine


register = template.Library()


@register.filter
def majestic_coins(value):
    try:
        amount = Decimal(str(value))
    except Exception:
        amount = Decimal("0")

    settings_obj = MajesticCoinSettings.load()
    return f"{amount:,.2f} {settings_obj.coin_symbol}"


@register.filter
def majestic_coin_value(value):
    try:
        amount = EconomyEngine.value_from_coins(value)
    except Exception:
        amount = Decimal("0.00")

    return f"${amount:,.2f}"


@register.simple_tag
def majestic_coin_symbol():
    return MajesticCoinSettings.load().coin_symbol
