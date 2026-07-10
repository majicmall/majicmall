from django.conf import settings
from django.db import models

from merchant.models import MerchantStore, Order


class DeliveryPartner(models.Model):
    CONTRACTOR_AGREEMENT_VERSION = "1.0"

    STATUS_CHOICES = [
        ("offline", "Offline"),
        ("available", "Available"),
        ("busy", "Busy"),
    ]

    VEHICLE_CHOICES = [
        ("car", "Car"),
        ("bike", "Bike"),
        ("scooter", "Scooter"),
        ("walking", "Walking"),
        ("other", "Other"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="delivery_partner",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="offline",
    )

    vehicle_type = models.CharField(
        max_length=20,
        choices=VEHICLE_CHOICES,
        default="car",
    )

    home_zip = models.CharField(max_length=20, blank=True)
    current_zip = models.CharField(max_length=20, blank=True)
    service_radius_miles = models.PositiveIntegerField(default=10)
    phone = models.CharField(max_length=30, blank=True)

    completed_deliveries = models.PositiveIntegerField(default=0)

    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=5.00,
    )

    today_earnings = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    weekly_earnings = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    contractor_agreement_accepted = models.BooleanField(default=False)

    contractor_agreement_accepted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    contractor_agreement_version = models.CharField(
        max_length=20,
        blank=True,
    )

    onboarding_completed = models.BooleanField(default=False)

    onboarding_completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Delivery Partner"
        verbose_name_plural = "Delivery Partners"

    def __str__(self):
        return f"{self.user.username} - {self.get_status_display()}"

    @property
    def full_name(self):
        full_name = self.user.get_full_name().strip()
        return full_name or self.user.username

    @property
    def is_ready_for_command_center(self):
        return bool(
            self.onboarding_completed
            and self.contractor_agreement_accepted
            and self.home_zip
            and self.current_zip
            and self.phone
            and self.is_active
        )


class DeliveryJob(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("offered", "Offered"),
        ("accepted", "Accepted"),
        ("picked_up", "Picked Up"),
        ("out_for_delivery", "Out For Delivery"),
        ("delivered", "Delivered"),
        ("canceled", "Canceled"),
    ]

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="delivery_job",
    )

    store = models.ForeignKey(
        MerchantStore,
        on_delete=models.CASCADE,
        related_name="delivery_jobs",
    )

    partner = models.ForeignKey(
        DeliveryPartner,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="delivery_jobs",
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="pending",
    )

    pickup_zip = models.CharField(max_length=20, blank=True)
    delivery_zip = models.CharField(max_length=20, blank=True)

    delivery_fee = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
    )

    tip_amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
    )

    pickup_notes = models.TextField(blank=True)
    delivery_notes = models.TextField(blank=True)

    accepted_at = models.DateTimeField(null=True, blank=True)
    picked_up_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Delivery Job"
        verbose_name_plural = "Delivery Jobs"

    def __str__(self):
        return f"Delivery Job #{self.id} - Order #{self.order_id}"

    @property
    def total_driver_payout(self):
        return self.delivery_fee + self.tip_amount
