from django.conf import settings
from django.db import models


class CustomerProfile(models.Model):
    """
    MajicMall Megaverse Customer Account
    """

    TIER_BRONZE = "bronze"
    TIER_SILVER = "silver"
    TIER_GOLD = "gold"
    TIER_PLATINUM = "platinum"

    TIER_CHOICES = [
        (TIER_BRONZE, "Bronze"),
        (TIER_SILVER, "Silver"),
        (TIER_GOLD, "Gold"),
        (TIER_PLATINUM, "Platinum"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="customer_profile",
    )

    phone = models.CharField(
        max_length=30,
        blank=True,
    )

    birthday = models.DateField(
        null=True,
        blank=True,
    )

    profile_photo = models.ImageField(
        upload_to="customers/profile/",
        blank=True,
        null=True,
    )

    loyalty_points = models.PositiveIntegerField(default=0)

    loyalty_tier = models.CharField(
        max_length=20,
        choices=TIER_CHOICES,
        default=TIER_BRONZE,
    )

    favorite_store_count = models.PositiveIntegerField(default=0)

    wishlist_count = models.PositiveIntegerField(default=0)

    notifications_enabled = models.BooleanField(default=True)

    sms_enabled = models.BooleanField(default=False)

    newsletter = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user__username"]

    def __str__(self):
        return f"{self.user.username}"


class CustomerAddress(models.Model):

    customer = models.ForeignKey(
        CustomerProfile,
        on_delete=models.CASCADE,
        related_name="addresses",
    )

    nickname = models.CharField(max_length=50)

    full_name = models.CharField(max_length=200)

    company = models.CharField(
        max_length=200,
        blank=True,
    )

    address1 = models.CharField(max_length=200)

    address2 = models.CharField(
        max_length=200,
        blank=True,
    )

    city = models.CharField(max_length=100)

    state = models.CharField(max_length=100)

    postal_code = models.CharField(max_length=20)

    country = models.CharField(
        max_length=100,
        default="United States",
    )

    default = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-default", "nickname"]

    def __str__(self):
        return f"{self.nickname} - {self.city}"