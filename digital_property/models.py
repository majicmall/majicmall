from django.core.exceptions import ValidationError
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

    class InventoryTier(models.TextChoices):
        STANDARD = "standard", "Standard"
        PREMIUM = "premium", "Premium"
        SIGNATURE = "signature", "Majestic Square Signature"

    class InventoryMode(models.TextChoices):
        EXCLUSIVE = "exclusive", "Exclusive"
        ROTATING = "rotating", "Rotating"
        HYBRID = "hybrid", "Hybrid"


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

    inventory_mode = models.CharField(
        max_length=20,
        choices=InventoryMode.choices,
        default=InventoryMode.HYBRID,
        db_index=True,
        help_text=(
            "Exclusive allows one advertiser, Rotating allows shared "
            "positions, and Hybrid supports either option."
        ),
    )

    display_seconds = models.PositiveIntegerField(
        default=10,
        help_text=(
            "Number of seconds each advertisement remains visible "
            "during a rotation."
        ),
    )

    rotation_capacity = models.PositiveIntegerField(
        default=10,
        help_text=(
            "Maximum number of advertiser positions available in "
            "the rotation."
        ),
    )

    inventory_tier = models.CharField(
        max_length=20,
        choices=InventoryTier.choices,
        default=InventoryTier.STANDARD,
        db_index=True,
        help_text=(
            "Standard, Premium, or Majestic Square Signature inventory."
        ),
    )

    minimum_spend = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=25,
        help_text=(
            "Minimum total campaign budget required when this property "
            "is selected."
        ),
    )

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

    @property
    def rotation_loop_seconds(self):
        if self.inventory_mode == self.InventoryMode.EXCLUSIVE:
            return self.display_seconds

        return self.display_seconds * self.rotation_capacity

    @property
    def total_plays_per_hour(self):
        if not self.display_seconds:
            return 0

        return int(3600 / self.display_seconds)

    @property
    def total_plays_per_day(self):
        return self.total_plays_per_hour * 24

    @property
    def total_plays_per_month(self):
        return self.total_plays_per_day * 30

    @property
    def advertiser_plays_per_hour(self):
        if self.inventory_mode == self.InventoryMode.EXCLUSIVE:
            return self.total_plays_per_hour

        if not self.rotation_loop_seconds:
            return 0

        return int(3600 / self.rotation_loop_seconds)

    @property
    def advertiser_plays_per_day(self):
        return self.advertiser_plays_per_hour * 24

    @property
    def advertiser_plays_per_month(self):
        return self.advertiser_plays_per_day * 30

    @property
    def reserved_rotation_positions(self):
        return sum(
            placement.positions_reserved
            for placement in self.campaign_placements.filter(
                campaign__status__in=(
                    "approved",
                    "scheduled",
                    "active",
                ),
                booking_mode="rotating",
            )
        )

    @property
    def has_exclusive_booking(self):
        return self.campaign_placements.filter(
            campaign__status__in=(
                "approved",
                "scheduled",
                "active",
            ),
            booking_mode="exclusive",
        ).exists()

    @property
    def available_rotation_positions(self):
        if self.has_exclusive_booking:
            return 0

        return max(
            self.rotation_capacity
            - self.reserved_rotation_positions,
            0,
        )

    @property
    def rotation_occupancy_percent(self):
        if self.has_exclusive_booking:
            return 100.0

        if not self.rotation_capacity:
            return 0.0

        return round(
            (
                self.reserved_rotation_positions
                / self.rotation_capacity
            )
            * 100,
            1,
        )

    @property
    def current_rotation_revenue(self):
        return sum(
            placement.agreed_price
            * placement.positions_reserved
            for placement in self.campaign_placements.filter(
                campaign__status__in=(
                    "approved",
                    "scheduled",
                    "active",
                ),
                booking_mode="rotating",
            )
        )

    @property
    def exclusive_revenue(self):
        return sum(
            placement.agreed_price
            for placement in self.campaign_placements.filter(
                campaign__status__in=(
                    "approved",
                    "scheduled",
                    "active",
                ),
                booking_mode="exclusive",
            )
        )

    @property
    def current_revenue(self):
        return self.current_rotation_revenue + self.exclusive_revenue

    @property
    def potential_rotation_revenue(self):
        plan = self.lease_plans.filter(
            active=True,
        ).order_by("price").first()

        if plan is None:
            return 0

        return plan.price * self.rotation_capacity

    def __str__(self):
        return f"{self.property_code} — {self.name}"


class PropertyLease(models.Model):
    """
    A leasing contract connecting a MerchantStore to a DigitalProperty
    through an approved LeasePlan.
    """

    class LeaseStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        RESERVED = "reserved", "Reserved"
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    lease_number = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
        blank=True,
        null=True,
        help_text="Permanent public lease reference generated automatically.",
    )

    merchant_store = models.ForeignKey(
        "merchant.MerchantStore",
        on_delete=models.PROTECT,
        related_name="property_leases",
    )

    digital_property = models.ForeignKey(
        DigitalProperty,
        on_delete=models.PROTECT,
        related_name="property_leases",
    )

    lease_plan = models.ForeignKey(
        LeasePlan,
        on_delete=models.PROTECT,
        related_name="property_leases",
    )

    status = models.CharField(
        max_length=20,
        choices=LeaseStatus.choices,
        default=LeaseStatus.PENDING,
        db_index=True,
    )

    start_date = models.DateField(
        help_text="First calendar date covered by this lease.",
    )

    end_date = models.DateField(
        help_text="Final calendar date covered by this lease.",
    )

    amount_paid = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Final amount paid for this lease.",
    )

    auto_renew = models.BooleanField(default=False)

    campaign_name = models.CharField(
        max_length=180,
        blank=True,
        help_text="Optional merchant-facing advertising campaign name.",
    )

    notes = models.TextField(
        blank=True,
        help_text="Internal administrative notes about this lease.",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Property Lease"
        verbose_name_plural = "Property Leases"
        indexes = [
            models.Index(
                fields=["digital_property", "status"],
                name="dp_lease_property_status_idx",
            ),
            models.Index(
                fields=["merchant_store", "status"],
                name="dp_lease_merchant_status_idx",
            ),
            models.Index(
                fields=["start_date", "end_date"],
                name="dp_lease_date_range_idx",
            ),
        ]

    def __str__(self):
        reference = self.lease_number or "Unnumbered Lease"
        return (
            f"{reference} — "
            f"{self.merchant_store.store_name} — "
            f"{self.digital_property.name}"
        )

    def clean(self):
        super().clean()

        errors = {}

        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                errors["end_date"] = (
                    "The lease end date cannot be earlier than "
                    "the lease start date."
                )

        if (
            self.digital_property_id
            and self.lease_plan_id
            and not self.digital_property.lease_plans.filter(
                pk=self.lease_plan_id
            ).exists()
        ):
            errors["lease_plan"] = (
                "The selected lease plan is not assigned to this "
                "digital property."
            )

        if self.amount_paid is not None and self.amount_paid < 0:
            errors["amount_paid"] = (
                "The amount paid cannot be negative."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        """
        Generate a stable public lease number after Django assigns the
        database primary key.
        """
        super().save(*args, **kwargs)

        if not self.lease_number:
            generated_number = f"LEASE-{self.pk:06d}"

            type(self).objects.filter(
                pk=self.pk,
                lease_number__isnull=True,
            ).update(
                lease_number=generated_number,
            )

            self.lease_number = generated_number

    @property
    def duration_days(self):
        if not self.start_date or not self.end_date:
            return 0

        return (self.end_date - self.start_date).days + 1

