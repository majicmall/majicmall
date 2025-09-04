# core/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings

from .models import Merchant
from merchant.models import MerchantStore


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_merchant_for_user(sender, instance, created, **kwargs):
    """
    Automatically create a Merchant profile AND a default MerchantStore
    whenever a User is created.
    """
    if created and not hasattr(instance, "merchant"):
        # Create Merchant profile
        merchant = Merchant.objects.create(
            user=instance,
            display_name=instance.username,
            slug=f"merchant-{instance.pk}",  # simple default slug
            email=instance.email or "",
            plan="starter",  # default plan
        )

        # 🚀 Auto-create the first store linked to this user
        MerchantStore.objects.create(
            owner=instance,
            store_name=f"{instance.username}'s Store",
            slogan="Welcome to my store!",
            category="General",
            plan="starter",
            description="This is your first store inside Majic Mall.",
        )
