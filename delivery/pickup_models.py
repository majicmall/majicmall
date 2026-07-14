from django.db import models


class MerchantPickupAddress(models.Model):
    """
    Exact physical pickup location used by the
    MajicMall Megaverse Driver Network.

    This record is separate from the public storefront presentation
    and is visible only to the merchant, assigned driver, and admins.
    """

    store = models.OneToOneField(
        "merchant.MerchantStore",
        on_delete=models.CASCADE,
        related_name="driver_pickup_address",
    )

    address_line_1 = models.CharField(
        max_length=255,
        verbose_name="Street Address",
    )

    address_line_2 = models.CharField(
        max_length=120,
        blank=True,
        verbose_name="Suite, Unit, Floor, or Building",
    )

    city = models.CharField(
        max_length=100,
    )

    state = models.CharField(
        max_length=100,
    )

    postal_code = models.CharField(
        max_length=20,
        verbose_name="ZIP / Postal Code",
    )

    pickup_instructions = models.TextField(
        blank=True,
        help_text=(
            "Examples: Use the rear entrance, ask for the manager, "
            "park in pickup space number 3, or ring the loading-door bell."
        ),
    )

    is_verified = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        app_label = "delivery"
        verbose_name = "Merchant Pickup Address"
        verbose_name_plural = "Merchant Pickup Addresses"

    def __str__(self):
        return f"{self.store.store_name} pickup location"

    @property
    def full_address(self):
        parts = [
            self.address_line_1,
            self.address_line_2,
            self.city,
            self.state,
            self.postal_code,
        ]

        return ", ".join(
            str(value).strip()
            for value in parts
            if str(value or "").strip()
        )
