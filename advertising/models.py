from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


def validate_creative_file_extension(uploaded_file):
    """
    Validate the uploaded file using the extensions supported by the
    MajicMall Media Network creative library.
    """
    extension = Path(uploaded_file.name).suffix.lower()

    allowed_extensions = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".gif",
        ".svg",
        ".mp3",
        ".wav",
        ".aac",
        ".m4a",
        ".ogg",
        ".mp4",
        ".mov",
        ".webm",
        ".m4v",
        ".pdf",
    }

    if extension not in allowed_extensions:
        supported = ", ".join(sorted(allowed_extensions))
        raise ValidationError(
            f"Unsupported creative file type '{extension}'. "
            f"Supported file types: {supported}"
        )


def creative_upload_path(instance, filename):
    """
    Organize creative uploads by campaign and media type.
    """
    campaign_id = instance.campaign_id or "unassigned"
    media_type = instance.media_type or "other"

    return (
        f"advertising/campaigns/{campaign_id}/"
        f"{media_type.lower()}/{filename}"
    )


class Campaign(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING = "pending", "Pending Approval"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CHANGES_REQUESTED = (
            "changes_requested",
            "Changes Requested",
        )
        SCHEDULED = "scheduled", "Scheduled"
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    name = models.CharField(
        max_length=200,
        help_text="Internal campaign name.",
    )

    advertiser_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Merchant, organization, artist, sponsor, or advertiser.",
    )

    description = models.TextField(
        blank=True,
        help_text="Campaign objective, message, and internal notes.",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )

    start_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date and time the campaign may begin.",
    )

    end_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date and time the campaign should stop.",
    )

    budget = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Optional total campaign budget.",
    )

    internal_notes = models.TextField(
        blank=True,
        help_text="Private notes for MajicMall Media Network staff.",
    )

    review_notes = models.TextField(
        blank=True,
        help_text=(
            "Approval, rejection, or requested-change notes."
        ),
    )

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="advertising_campaigns_reviewed",
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    approved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="advertising_campaigns_created",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Advertising Campaign"
        verbose_name_plural = "Advertising Campaigns"

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()

        if self.start_at and self.end_at and self.end_at <= self.start_at:
            raise ValidationError(
                {"end_at": "The campaign end must occur after its start."}
            )

    @property
    def is_currently_running(self):
        now = timezone.now()

        if self.status != self.Status.ACTIVE:
            return False

        if self.start_at and now < self.start_at:
            return False

        if self.end_at and now >= self.end_at:
            return False

        return True

    @property
    def total_impressions(self):
        return sum(
            creative.impressions
            for creative in self.creatives.all()
        )

    @property
    def total_clicks(self):
        return sum(
            creative.clicks
            for creative in self.creatives.all()
        )

    @property
    def click_through_rate(self):
        impressions = self.total_impressions

        if not impressions:
            return 0

        return round((self.total_clicks / impressions) * 100, 2)


class AdvertisingCreative(models.Model):
    class MediaType(models.TextChoices):
        BILLBOARD = "billboard", "Digital Billboard"
        BANNER = "banner", "Banner Advertisement"
        IMAGE = "image", "Image Advertisement"
        AUDIO = "audio", "Audio Commercial"
        VIDEO = "video", "Video Advertisement"
        THEATER_PREROLL = "theater_preroll", "Theater Pre-Roll"
        RADIO_SPOT = "radio_spot", "Music Zone Radio Spot"
        MOBILE_PROMOTION = "mobile_promotion", "Mobile Promotion"
        PUBLIC_ANNOUNCEMENT = "public_announcement", "Public Announcement"
        OTHER = "other", "Other Creative"

    class ApprovalStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING = "pending", "Pending Review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        ARCHIVED = "archived", "Archived"

    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name="creatives",
    )

    title = models.CharField(max_length=200)

    media_type = models.CharField(
        max_length=30,
        choices=MediaType.choices,
        default=MediaType.BANNER,
        db_index=True,
    )

    approval_status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.DRAFT,
        db_index=True,
    )

    file = models.FileField(
        upload_to=creative_upload_path,
        validators=[validate_creative_file_extension],
        blank=True,
        null=True,
    )

    external_media_url = models.URLField(
        blank=True,
        help_text=(
            "Optional externally hosted media or streaming URL."
        ),
    )

    destination_url = models.URLField(
        blank=True,
        help_text="Where visitors should go when they click the advertisement.",
    )

    headline = models.CharField(
        max_length=255,
        blank=True,
    )

    call_to_action = models.CharField(
        max_length=80,
        blank=True,
        help_text="Examples: Visit Store, Learn More, Buy Tickets.",
    )

    alt_text = models.CharField(
        max_length=255,
        blank=True,
        help_text="Accessibility description for visual advertisements.",
    )

    target_zones = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "Temporary list of zone names or slugs. "
            "A direct zone relationship can be added in a later push."
        ),
    )

    placement_codes = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "Placement identifiers such as home_billboard, "
            "directory_banner, or theater_preroll."
        ),
    )

    priority = models.PositiveIntegerField(
        default=100,
        help_text="Lower numbers receive higher display priority.",
    )

    play_frequency = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="Relative rotation frequency for this creative.",
    )

    duration_seconds = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Optional duration for audio or video creatives.",
    )

    start_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Optional creative-specific start date and time.",
    )

    end_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Optional creative-specific end date and time.",
    )

    is_enabled = models.BooleanField(default=True)

    impressions = models.PositiveBigIntegerField(default=0)
    clicks = models.PositiveBigIntegerField(default=0)

    review_notes = models.TextField(
        blank=True,
        help_text="Approval, rejection, or production notes.",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="advertising_creatives_created",
    )

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="advertising_creatives_reviewed",
    )

    reviewed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("priority", "-created_at")
        verbose_name = "Advertising Creative"
        verbose_name_plural = "Advertising Creatives"

    def __str__(self):
        return f"{self.title} — {self.get_media_type_display()}"

    def clean(self):
        super().clean()

        errors = {}

        if not self.file and not self.external_media_url:
            errors["file"] = (
                "Upload a creative file or provide an external media URL."
            )

        if self.start_at and self.end_at and self.end_at <= self.start_at:
            errors["end_at"] = (
                "The creative end must occur after its start."
            )

        if errors:
            raise ValidationError(errors)

    @property
    def click_through_rate(self):
        if not self.impressions:
            return 0

        return round((self.clicks / self.impressions) * 100, 2)

    @property
    def is_currently_eligible(self):
        now = timezone.now()

        if not self.is_enabled:
            return False

        if self.approval_status != self.ApprovalStatus.APPROVED:
            return False

        if not self.campaign.is_currently_running:
            return False

        if self.start_at and now < self.start_at:
            return False

        if self.end_at and now >= self.end_at:
            return False

        return True


class CampaignPlacement(models.Model):
    class BookingMode(models.TextChoices):
        EXCLUSIVE = "exclusive", "Exclusive Property"
        ROTATING = "rotating", "Rotating Position"

    """
    Connect an advertising campaign to a DigitalProperty and LeasePlan.
    One campaign budget may fund multiple placement records.
    """

    booking_mode = models.CharField(
        max_length=20,
        choices=BookingMode.choices,
        default=BookingMode.ROTATING,
        db_index=True,
    )

    positions_reserved = models.PositiveIntegerField(
        default=1,
        help_text=(
            "Number of rotating advertising positions purchased. "
            "Exclusive bookings always reserve the full property."
        ),
    )

    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name="placements",
    )

    digital_property = models.ForeignKey(
        "digital_property.DigitalProperty",
        on_delete=models.PROTECT,
        related_name="campaign_placements",
    )

    lease_plan = models.ForeignKey(
        "digital_property.LeasePlan",
        on_delete=models.PROTECT,
        related_name="campaign_placements",
    )

    start_at = models.DateTimeField()

    end_at = models.DateTimeField()

    agreed_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = (
            "start_at",
            "digital_property__display_order",
            "digital_property__name",
        )
        constraints = [
            models.UniqueConstraint(
                fields=(
                    "campaign",
                    "digital_property",
                ),
                name="unique_campaign_digital_property",
            ),
        ]
        verbose_name = "Campaign Placement"
        verbose_name_plural = "Campaign Placements"

    def __str__(self):
        return (
            f"{self.campaign.name} — "
            f"{self.digital_property.property_code}"
        )

    def clean(self):
        super().clean()

        errors = {}

        if self.positions_reserved < 1:
            errors["positions_reserved"] = (
                "At least one rotation position is required."
            )

        if self.digital_property_id:
            property_mode = self.digital_property.inventory_mode

            if (
                self.booking_mode == self.BookingMode.EXCLUSIVE
                and property_mode
                == self.digital_property.InventoryMode.ROTATING
            ):
                errors["booking_mode"] = (
                    "This property only accepts rotating bookings."
                )

            if (
                self.booking_mode == self.BookingMode.ROTATING
                and property_mode
                == self.digital_property.InventoryMode.EXCLUSIVE
            ):
                errors["booking_mode"] = (
                    "This property only accepts exclusive bookings."
                )

            open_placements = type(self).objects.filter(
                digital_property=self.digital_property,
                campaign__status__in=(
                    "approved",
                    "scheduled",
                    "active",
                ),
            ).exclude(pk=self.pk)

            if self.campaign_id:
                open_placements = open_placements.exclude(
                    campaign_id=self.campaign_id,
                )

            exclusive_exists = open_placements.filter(
                booking_mode=self.BookingMode.EXCLUSIVE,
            ).exists()

            rotating_reserved = sum(
                placement.positions_reserved
                for placement in open_placements.filter(
                    booking_mode=self.BookingMode.ROTATING,
                )
            )

            if (
                self.booking_mode == self.BookingMode.EXCLUSIVE
                and open_placements.exists()
            ):
                errors["booking_mode"] = (
                    "This property already has active or scheduled "
                    "advertising bookings."
                )

            if (
                self.booking_mode == self.BookingMode.ROTATING
                and exclusive_exists
            ):
                errors["booking_mode"] = (
                    "This property currently has an exclusive booking."
                )

            if self.booking_mode == self.BookingMode.EXCLUSIVE:
                self.positions_reserved = (
                    self.digital_property.rotation_capacity
                )

            if self.booking_mode == self.BookingMode.ROTATING:
                remaining = max(
                    self.digital_property.rotation_capacity
                    - rotating_reserved,
                    0,
                )

                if self.positions_reserved > remaining:
                    errors["positions_reserved"] = (
                        f"Only {remaining} rotation position"
                        f"{'s are' if remaining != 1 else ' is'} "
                        "currently available."
                    )

        if self.start_at and self.end_at:
            if self.end_at <= self.start_at:
                errors["end_at"] = (
                    "The placement end must occur after its start."
                )

        if (
            self.digital_property_id
            and self.lease_plan_id
            and not self.digital_property.lease_plans.filter(
                pk=self.lease_plan_id
            ).exists()
        ):
            errors["lease_plan"] = (
                "This lease plan is not available for the selected "
                "advertising property."
            )

        overlapping = type(self).objects.filter(
            digital_property_id=self.digital_property_id,
            start_at__lt=self.end_at,
            end_at__gt=self.start_at,
        ).exclude(pk=self.pk)

        if self.campaign_id:
            overlapping = overlapping.exclude(
                campaign_id=self.campaign_id,
            )

        if (
            self.digital_property_id
            and self.start_at
            and self.end_at
            and overlapping.exists()
        ):
            errors["digital_property"] = (
                "This advertising location is already scheduled during "
                "the selected campaign dates."
            )

        if errors:
            raise ValidationError(errors)

