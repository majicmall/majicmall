from decimal import Decimal

from django.apps import apps
from django.conf import settings
from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver

from .models import (
    CitizenLevelReward,
    MajesticCoinSettings,
    MajestianWallet,
)


@receiver(
    post_save,
    sender=settings.AUTH_USER_MODEL,
    dispatch_uid="majestian_economy_create_wallet",
)
def create_majestian_wallet(sender, instance, created, **kwargs):
    if created:
        MajestianWallet.objects.get_or_create(user=instance)


@receiver(
    post_migrate,
    dispatch_uid="majestian_economy_seed_defaults",
)
def seed_majestian_economy_defaults(sender, app_config=None, **kwargs):
    if app_config and app_config.label != "majestian_economy":
        return

    if not apps.is_installed("majestian_economy"):
        return

    MajesticCoinSettings.objects.get_or_create(
        pk=1,
        defaults={
            "coin_name": "Majestic Coin",
            "coin_symbol": "MC",
            "currency_code": "USD",
            "coin_value": Decimal("0.1000"),
            "minimum_redemption_coins": Decimal("100.00"),
            "maximum_daily_redemption_coins": Decimal("5000.00"),
            "reward_hold_days": 7,
        },
    )

    default_levels = (
        {
            "name": "Vision",
            "slug": "vision",
            "referral_percentage": Decimal("10.000"),
            "display_order": 10,
            "description": (
                "Vision Majestian recommendation reward level."
            ),
        },
        {
            "name": "Pro",
            "slug": "pro",
            "referral_percentage": Decimal("12.000"),
            "display_order": 20,
            "description": (
                "Pro Majestian recommendation reward level."
            ),
        },
        {
            "name": "Elite",
            "slug": "elite",
            "referral_percentage": Decimal("15.000"),
            "display_order": 30,
            "description": (
                "Elite Majestian recommendation reward level."
            ),
        },
        {
            "name": "Majestic",
            "slug": "majestic",
            "referral_percentage": Decimal("20.000"),
            "display_order": 40,
            "description": (
                "Majestic Majestian recommendation reward level."
            ),
        },
    )

    for level in default_levels:
        CitizenLevelReward.objects.update_or_create(
            slug=level["slug"],
            defaults=level,
        )
