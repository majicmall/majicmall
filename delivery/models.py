from django.conf import settings
from django.db import models

from merchant.models import MerchantStore, Order


def driver_verification_upload_path(instance, filename):
    """
    Organize driver verification files by driver account.

    Production note:
    Sensitive verification documents should ultimately be stored
    in private cloud storage rather than publicly accessible media.
    """
    user_id = instance.user_id or "unassigned"
    safe_filename = filename.replace(" ", "_")
    return f"driver_verification/{user_id}/{safe_filename}"


class DeliveryPartner(models.Model):
    CONTRACTOR_AGREEMENT_VERSION = "1.0"

    STATUS_CHOICES = [
        ("offline", "Offline"),
        ("available", "Available"),
        ("busy", "Busy"),
    ]

    APPROVAL_STATUS_CHOICES = [
        ("pending", "Pending Approval"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
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

    street_address = models.CharField(max_length=255, blank=True)
    address_line_2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=120, blank=True)
    state = models.CharField(max_length=2, blank=True)

    home_zip = models.CharField(max_length=20, blank=True)
    current_zip = models.CharField(max_length=20, blank=True)
    service_radius_miles = models.PositiveIntegerField(default=10)
    phone = models.CharField(max_length=30, blank=True)

    address_verified = models.BooleanField(default=False)

    address_verified_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    profile_photo = models.ImageField(
        upload_to=driver_verification_upload_path,
        blank=True,
        null=True,
    )

    vehicle_photo = models.ImageField(
        upload_to=driver_verification_upload_path,
        blank=True,
        null=True,
    )

    driver_license_document = models.FileField(
        upload_to=driver_verification_upload_path,
        blank=True,
        null=True,
    )

    insurance_document = models.FileField(
        upload_to=driver_verification_upload_path,
        blank=True,
        null=True,
    )

    vehicle_registration_document = models.FileField(
        upload_to=driver_verification_upload_path,
        blank=True,
        null=True,
    )

    vehicle_make = models.CharField(
        max_length=80,
        blank=True,
    )

    vehicle_model = models.CharField(
        max_length=80,
        blank=True,
    )

    vehicle_year = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    vehicle_color = models.CharField(
        max_length=50,
        blank=True,
    )

    license_plate = models.CharField(
        max_length=30,
        blank=True,
    )

    documents_reviewed = models.BooleanField(default=False)

    documents_reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

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

    approval_status = models.CharField(
        max_length=20,
        choices=APPROVAL_STATUS_CHOICES,
        default="pending",
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_delivery_partners",
    )

    deactivated_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    account_notes = models.TextField(
        blank=True,
        help_text=(
            "Internal notes about approval, rejection, suspension, "
            "or deactivation."
        ),
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
    def full_address(self):
        pieces = [
            self.street_address,
            self.address_line_2,
            self.city,
            self.state,
            self.home_zip,
        ]

        return ", ".join(piece for piece in pieces if piece)

    @property
    def vehicle_description(self):
        details = [
            self.vehicle_year,
            self.vehicle_make,
            self.vehicle_model,
            self.vehicle_color,
        ]

        return " ".join(
            str(detail).strip()
            for detail in details
            if detail
        )

    @property
    def verification_items(self):
        return {
            "profile_photo": bool(self.profile_photo),
            "vehicle_information": bool(
                self.vehicle_make
                and self.vehicle_model
                and self.vehicle_year
                and self.vehicle_color
                and self.license_plate
            ),
            "vehicle_photo": bool(self.vehicle_photo),
            "driver_license": bool(self.driver_license_document),
            "insurance": bool(self.insurance_document),
            "vehicle_registration": bool(
                self.vehicle_registration_document
            ),
        }

    @property
    def verification_completed_items(self):
        return sum(self.verification_items.values())

    @property
    def verification_total_items(self):
        return len(self.verification_items)

    @property
    def verification_percentage(self):
        total = self.verification_total_items

        if not total:
            return 0

        return round(
            self.verification_completed_items / total * 100
        )

    @property
    def verification_documents_complete(self):
        return all(self.verification_items.values())

    @property
    def is_approved(self):
        return self.approval_status == "approved"

    @property
    def can_accept_deliveries(self):
        return bool(
            self.is_ready_for_command_center
            and self.status == "available"
        )

    @property
    def is_ready_for_command_center(self):
        return bool(
            self.onboarding_completed
            and self.contractor_agreement_accepted
            and self.address_verified
            and self.street_address
            and self.city
            and self.state
            and self.home_zip
            and self.current_zip
            and self.phone
            and self.approval_status == "approved"
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
