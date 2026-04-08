from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.exceptions import FieldDoesNotExist

from .models import Merchant
from merchant.models import MerchantStore


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_merchant_for_user(sender, instance, created, **kwargs):
    """
    Auto-create a Merchant profile AND a default MerchantStore when a User is created.
    Safe against duplicate creation and compatible with newer MerchantStore fields.
    """
    if not created:
        return

    display_name = instance.username or instance.email or "New User"

    # Create Merchant profile if missing
    Merchant.objects.get_or_create(
        user=instance,
        defaults={
            "display_name": display_name,
            "slug": f"merchant-{instance.pk}",
            "email": instance.email or "",
            "plan": "starter",
        },
    )

    # Avoid duplicate store creation
    existing_store = MerchantStore.objects.filter(owner=instance).first()
    if existing_store:
        return

    # Build kwargs for MerchantStore
    store_kwargs = dict(
        owner=instance,
        store_name=f"{display_name}'s Store" if display_name else "My Store",
        category="General",
        slogan="Welcome to my store!",
        description="This is your first store inside Majic Mall.",
        plan="starter",
    )

    # Optional fields if they exist on the current model
    optional_fields = {
        "is_public": False,
        "contact_person": display_name,
        "contact_email": instance.email or "",
        "contact_phone": "",
        "is_featured": False,
        "featured_slot": None,
        "admin_notes": "",
    }

    for field_name, value in optional_fields.items():
        try:
            MerchantStore._meta.get_field(field_name)
            store_kwargs[field_name] = value
        except FieldDoesNotExist:
            pass

    MerchantStore.objects.create(**store_kwargs)
