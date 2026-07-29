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

class DigitalProperty(models.Model):
    """
    A leasable digital advertising or promotional location inside
    MajicMall Megaverse.
    """

    class AvailabilityStatus(models.TextChoices):
        AVAILABLE = "available", "Available"
        RESERVED = "reserved", "Reserved"
        LEASED = "leased", "Leased"
        MAINTENANCE = "maintenance", "Maintenance"
        COMING_SOON = "coming_soon", "Coming Soon"

    property_code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Permanent inventory code, such as MM-BB-0001.",
    )

    name = models.CharField(max_length=150)

    slug = models.SlugField(
        max_length=170,
        unique=True,
    )

    property_type = models.ForeignKey(
        PropertyType,
        on_delete=models.PROTECT,
        related_name="digital_properties",
    )

    mall_zone = models.ForeignKey(
        "merchant.MallZone",
        on_delete=models.PROTECT,
        related_name="digital_properties",
        null=True,
        blank=True,
        help_text="Leave blank for global properties such as the homepage hero.",
    )

    lease_plans = models.ManyToManyField(
        LeasePlan,
        related_name="digital_properties",
        blank=True,
    )

    description = models.TextField(blank=True)

    location_label = models.CharField(
        max_length=180,
        blank=True,
        help_text="Visible location description inside MajicMall Megaverse.",
    )

    width = models.PositiveIntegerField(
        default=1920,
        help_text="Recommended creative width in pixels.",
    )

    height = models.PositiveIntegerField(
        default=1080,
        help_text="Recommended creative height in pixels.",
    )

    supports_image = models.BooleanField(default=True)

    supports_video = models.BooleanField(default=False)

    interactive = models.BooleanField(default=False)

    availability_status = models.CharField(
        max_length=20,
        choices=AvailabilityStatus.choices,
        default=AvailabilityStatus.AVAILABLE,
    )

    featured = models.BooleanField(default=False)

    active = models.BooleanField(default=True)

    display_order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "name"]
        verbose_name = "Digital Property"
        verbose_name_plural = "Digital Properties"

    def __str__(self):
        return f"{self.property_code} — {self.name}"

