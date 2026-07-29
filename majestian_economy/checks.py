from django.core.checks import Error, register
from django.db.utils import OperationalError, ProgrammingError

from .models import MajesticCoinSettings


@register()
def majestic_economy_checks(app_configs, **kwargs):
    errors = []

    try:
        settings_obj = MajesticCoinSettings.objects.filter(pk=1).first()
    except (OperationalError, ProgrammingError):
        # Database tables may not exist yet during the first migration.
        return errors

    if settings_obj and settings_obj.coin_value <= 0:
        errors.append(
            Error(
                "Majestic Coin value must be greater than zero.",
                hint=(
                    "Open Majestic Economy settings in Django Admin and "
                    "enter a positive coin value."
                ),
                id="majestian_economy.E001",
            )
        )

    return errors
