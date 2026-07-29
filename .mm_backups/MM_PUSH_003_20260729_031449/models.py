from django.db import models


class PropertyType(models.Model):
    """
    Types of digital real estate inside MajicMall Megaverse.
    """

    name = models.CharField(max_length=100, unique=True)

    description = models.TextField(blank=True)

    active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Property Type"
        verbose_name_plural = "Property Types"

    def __str__(self):
        return self.name


class LeasePlan(models.Model):
    class BillingPeriod(models.TextChoices):
        DAILY = "daily", "Daily"
        WEEKLY = "weekly", "Weekly"
        MONTHLY = "monthly", "Monthly"
        YEARLY = "yearly", "Yearly"
        EVENT = "event", "Event"
        CUSTOM = "custom", "Custom"

    name = models.CharField(max_length=120, unique=True)

    description = models.TextField(blank=True)

    billing_period = models.CharField(
        max_length=20,
        choices=BillingPeriod.choices,
        default=BillingPeriod.MONTHLY,
    )

    duration_days = models.PositiveIntegerField(default=30)

    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    featured = models.BooleanField(default=False)

    active = models.BooleanField(default=True)

    display_order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "price", "name"]
        verbose_name = "Lease Plan"
        verbose_name_plural = "Lease Plans"

    def __str__(self):
        return f"{self.name} — ${self.price}"
