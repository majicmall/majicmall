# core/signals.py
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Merchant
from merchant.models import MerchantStore


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_merchant_for_user(sender, instance, created, **kwargs):
    """
    Auto-create a Merchant profile AND a default MerchantStore when a User is created.
    Idempotent: only runs on initial creation.
    """
    if not created:
        return

    # Create Merchant profile if missing
    Merchant.objects.get_or_create(
        user=instance,
        defaults={
            "display_name": instance.username or (instance.email or "New User"),
            "slug": f"merchant-{instance.pk}",
            "email": instance.email or "",
            "plan": "starter",
        },
    )

    # Create a default store for this user — explicitly set is_public to satisfy NOT NULL
    MerchantStore.objects.create(
        owner=instance,
        store_name=f"{(instance.username or 'My')}'s Store",
        category="General",
        slogan="Welcome to my store!",
        description="This is your first store inside Majic Mall.",
        plan="starter",
        is_public=False,  # <-- important for your current DB schema
    )

