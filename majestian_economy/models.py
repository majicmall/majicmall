from __future__ import annotations

import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class MajesticCoinSettings(TimeStampedModel):
    """
    Singleton configuration for the Majestic Coin economy.

    The initial MajicMall Megaverse standard is:

        1 Majestic Coin = $0.10 of platform value

    The value remains administrator-configurable so future economic policy
    changes do not require source-code changes.
    """

    coin_name = models.CharField(
        max_length=80,
        default="Majestic Coin",
    )
    coin_symbol = models.CharField(
        max_length=12,
        default="MC",
    )
    currency_code = models.CharField(
        max_length=3,
        default="USD",
    )
    coin_value = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=Decimal("0.1000"),
        help_text="Platform value represented by one Majestic Coin.",
    )

    minimum_redemption_coins = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("100.00"),
    )
    maximum_daily_redemption_coins = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("5000.00"),
    )

    referral_rewards_enabled = models.BooleanField(default=True)
    merchant_rewards_enabled = models.BooleanField(default=True)
    creator_rewards_enabled = models.BooleanField(default=True)
    purchase_rewards_enabled = models.BooleanField(default=False)
    redemption_enabled = models.BooleanField(default=False)
    bonus_events_enabled = models.BooleanField(default=True)

    require_payment_confirmation = models.BooleanField(default=True)
    reward_hold_days = models.PositiveIntegerField(
        default=7,
        help_text="Recommended holding period before a pending reward is posted.",
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Majestic Coin settings"
        verbose_name_plural = "Majestic Coin settings"

    def __str__(self):
        return f"{self.coin_name}: 1 {self.coin_symbol} = ${self.coin_value}"

    def clean(self):
        super().clean()

        if self.coin_value <= 0:
            raise ValidationError(
                {"coin_value": "Coin value must be greater than zero."}
            )

        if self.minimum_redemption_coins < 0:
            raise ValidationError(
                {
                    "minimum_redemption_coins":
                    "Minimum redemption cannot be negative."
                }
            )

        if self.maximum_daily_redemption_coins < 0:
            raise ValidationError(
                {
                    "maximum_daily_redemption_coins":
                    "Maximum daily redemption cannot be negative."
                }
            )

        if (
            self.maximum_daily_redemption_coins
            and self.minimum_redemption_coins
            > self.maximum_daily_redemption_coins
        ):
            raise ValidationError(
                "Minimum redemption cannot exceed the maximum daily redemption."
            )

    def save(self, *args, **kwargs):
        # This is a singleton model. The primary key always remains 1.
        self.pk = 1
        self.full_clean()
        return super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _created = cls.objects.get_or_create(
            pk=1,
            defaults={
                "coin_name": "Majestic Coin",
                "coin_symbol": "MC",
                "currency_code": "USD",
                "coin_value": Decimal("0.1000"),
            },
        )
        return obj


class CitizenLevelReward(TimeStampedModel):
    """
    Configurable referral percentages based on the referring Majestian's
    Citizen Level.
    """

    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=70, unique=True)
    referral_percentage = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        help_text="Percentage of a qualifying membership payment.",
    )
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    description = models.TextField(blank=True)

    class Meta:
        ordering = ("display_order", "name")
        verbose_name = "Citizen Level reward"
        verbose_name_plural = "Citizen Level rewards"

    def __str__(self):
        return f"{self.name}: {self.referral_percentage}%"

    def clean(self):
        super().clean()

        if self.referral_percentage < 0:
            raise ValidationError(
                {"referral_percentage": "Referral percentage cannot be negative."}
            )

        if self.referral_percentage > 100:
            raise ValidationError(
                {"referral_percentage": "Referral percentage cannot exceed 100%."}
            )


class MajestianWallet(TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        RESTRICTED = "restricted", "Restricted"
        SUSPENDED = "suspended", "Suspended"
        CLOSED = "closed", "Closed"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="majestian_wallet",
    )

    available_coins = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    pending_coins = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    lifetime_earned_coins = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    lifetime_redeemed_coins = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    lifetime_reversed_coins = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    lifetime_expired_coins = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )

    opportunity_score = models.PositiveBigIntegerField(
        default=0,
        help_text=(
            "Internal contribution score reserved for future Majestian "
            "recognition and leadership programs."
        ),
    )

    last_transaction_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("user_id",)
        verbose_name = "Majestian Wallet"
        verbose_name_plural = "Majestian Wallets"
        constraints = [
            models.CheckConstraint(
                condition=Q(available_coins__gte=0),
                name="majestian_wallet_available_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(pending_coins__gte=0),
                name="majestian_wallet_pending_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(lifetime_earned_coins__gte=0),
                name="majestian_wallet_earned_nonnegative",
            ),
        ]

    def __str__(self):
        display_name = (
            getattr(self.user, "get_full_name", lambda: "")()
            or getattr(self.user, "username", "")
            or getattr(self.user, "email", "")
            or f"Majestian #{self.user_id}"
        )
        return f"{display_name} — {self.available_coins} MC"

    @property
    def total_coins(self):
        return self.available_coins + self.pending_coins

    @property
    def available_platform_value(self):
        settings_obj = MajesticCoinSettings.load()
        return self.available_coins * settings_obj.coin_value

    @property
    def pending_platform_value(self):
        settings_obj = MajesticCoinSettings.load()
        return self.pending_coins * settings_obj.coin_value


class CoinTransaction(TimeStampedModel):
    class Direction(models.TextChoices):
        CREDIT = "credit", "Credit"
        DEBIT = "debit", "Debit"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        POSTED = "posted", "Posted"
        REVERSED = "reversed", "Reversed"
        CANCELLED = "cancelled", "Cancelled"

    class TransactionType(models.TextChoices):
        CITIZEN_REFERRAL = "citizen_referral", "Citizen recommendation"
        MERCHANT_REFERRAL = "merchant_referral", "Merchant recommendation"
        CREATOR_REFERRAL = "creator_referral", "Creator recommendation"
        PURCHASE_REWARD = "purchase_reward", "Purchase reward"
        CREATOR_REVENUE = "creator_revenue", "Creator revenue"
        AD_REVENUE = "ad_revenue", "Advertising revenue"
        SPONSORSHIP = "sponsorship", "Sponsorship revenue"
        FOUNDATION_BONUS = "foundation_bonus", "Foundation bonus"
        COMMUNITY_REWARD = "community_reward", "Community reward"
        PROMOTIONAL_BONUS = "promotional_bonus", "Promotional bonus"
        REDEMPTION = "redemption", "Redemption"
        EXPIRATION = "expiration", "Expiration"
        ADMIN_ADJUSTMENT = "admin_adjustment", "Administrative adjustment"
        REVERSAL = "reversal", "Reversal"
        OTHER = "other", "Other"

    public_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,
    )

    wallet = models.ForeignKey(
        MajestianWallet,
        on_delete=models.PROTECT,
        related_name="transactions",
    )

    transaction_type = models.CharField(
        max_length=40,
        choices=TransactionType.choices,
        db_index=True,
    )
    direction = models.CharField(
        max_length=10,
        choices=Direction.choices,
        db_index=True,
    )
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    coin_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        help_text="Always stored as a positive quantity.",
    )

    coin_value_snapshot = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        help_text="Value of one MC when this transaction was created.",
    )

    platform_value = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        help_text="Dollar value represented when the transaction was created.",
    )

    description = models.CharField(max_length=255)
    reference_type = models.CharField(max_length=100, blank=True)
    reference_id = models.CharField(max_length=150, blank=True)

    idempotency_key = models.CharField(
        max_length=190,
        unique=True,
        null=True,
        blank=True,
        help_text="Prevents a qualifying event from being rewarded twice.",
    )

    metadata = models.JSONField(default=dict, blank=True)

    available_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date a pending reward becomes eligible for posting.",
    )
    posted_at = models.DateTimeField(null=True, blank=True)
    reversed_at = models.DateTimeField(null=True, blank=True)

    reversal_of = models.OneToOneField(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="reversal_transaction",
    )

    class Meta:
        ordering = ("-created_at", "-id")
        verbose_name = "Coin transaction"
        verbose_name_plural = "Coin transactions"
        indexes = [
            models.Index(
                fields=("wallet", "status", "created_at"),
                name="mc_wallet_status_created",
            ),
            models.Index(
                fields=("transaction_type", "status"),
                name="mc_type_status",
            ),
            models.Index(
                fields=("reference_type", "reference_id"),
                name="mc_reference",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(coin_amount__gt=0),
                name="coin_transaction_amount_positive",
            ),
            models.CheckConstraint(
                condition=Q(coin_value_snapshot__gt=0),
                name="coin_transaction_value_positive",
            ),
            models.CheckConstraint(
                condition=Q(platform_value__gte=0),
                name="coin_transaction_platform_nonnegative",
            ),
        ]

    def __str__(self):
        sign = "+" if self.direction == self.Direction.CREDIT else "-"
        return (
            f"{sign}{self.coin_amount} MC — "
            f"{self.get_transaction_type_display()} — "
            f"{self.get_status_display()}"
        )

    def clean(self):
        super().clean()

        if self.coin_amount <= 0:
            raise ValidationError(
                {"coin_amount": "Coin amount must be greater than zero."}
            )

        if self.coin_value_snapshot <= 0:
            raise ValidationError(
                {
                    "coin_value_snapshot":
                    "The coin value snapshot must be greater than zero."
                }
            )

        expected_value = self.coin_amount * self.coin_value_snapshot

        if abs(expected_value - self.platform_value) > Decimal("0.02"):
            raise ValidationError(
                {
                    "platform_value":
                    "Platform value does not match the coin amount and value snapshot."
                }
            )

        if self.status == self.Status.POSTED and not self.posted_at:
            self.posted_at = timezone.now()

        if self.status == self.Status.REVERSED and not self.reversed_at:
            self.reversed_at = timezone.now()

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError(
            "Coin ledger entries are permanent and cannot be deleted. "
            "Create a reversal transaction instead."
        )


class MajestianRecommendation(TimeStampedModel):
    """
    Phase-one recommendation record.

    Payment-provider integration and automatic checkout attribution can connect
    to this record in the next Majestian Economy installer.
    """

    class RecommendationType(models.TextChoices):
        CITIZEN = "citizen", "Citizen"
        MERCHANT = "merchant", "Merchant"
        CREATOR = "creator", "Creator"
        NONPROFIT = "nonprofit", "Nonprofit"
        ORGANIZATION = "organization", "Organization"
        CITY = "city", "City"
        FESTIVAL = "festival", "Festival"
        KINGDOM = "kingdom", "Kingdom"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        TRACKED = "tracked", "Tracked"
        PENDING_PAYMENT = "pending_payment", "Pending payment"
        PAYMENT_CONFIRMED = "payment_confirmed", "Payment confirmed"
        REWARD_PENDING = "reward_pending", "Reward pending"
        REWARDED = "rewarded", "Rewarded"
        REJECTED = "rejected", "Rejected"
        REVERSED = "reversed", "Reversed"

    public_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,
    )

    referrer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="majestian_recommendations_made",
    )
    referred_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="majestian_recommendation_received",
        null=True,
        blank=True,
    )

    recommendation_type = models.CharField(
        max_length=20,
        choices=RecommendationType.choices,
        default=RecommendationType.CITIZEN,
        db_index=True,
    )

    citizen_level = models.ForeignKey(
        CitizenLevelReward,
        on_delete=models.PROTECT,
        related_name="recommendations",
        null=True,
        blank=True,
    )

    membership_name = models.CharField(max_length=120, blank=True)
    membership_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    reward_percentage_snapshot = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        default=Decimal("0.000"),
    )
    reward_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    coins_awarded = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    status = models.CharField(
        max_length=25,
        choices=Status.choices,
        default=Status.TRACKED,
        db_index=True,
    )

    referral_code = models.CharField(
        max_length=80,
        blank=True,
        db_index=True,
    )
    payment_reference = models.CharField(
        max_length=190,
        blank=True,
        db_index=True,
    )

    payment_confirmed_at = models.DateTimeField(null=True, blank=True)
    rewarded_at = models.DateTimeField(null=True, blank=True)

    reward_transaction = models.OneToOneField(
        CoinTransaction,
        on_delete=models.PROTECT,
        related_name="recommendation",
        null=True,
        blank=True,
    )

    fraud_review_required = models.BooleanField(default=False)
    fraud_review_notes = models.TextField(blank=True)
    administrator_notes = models.TextField(blank=True)

    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Majestian recommendation"
        verbose_name_plural = "Majestian recommendations"
        constraints = [
            models.CheckConstraint(
                condition=Q(membership_amount__gte=0),
                name="recommendation_membership_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(reward_percentage_snapshot__gte=0),
                name="recommendation_percentage_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(reward_value__gte=0),
                name="recommendation_reward_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(coins_awarded__gte=0),
                name="recommendation_coins_nonnegative",
            ),
        ]

    def __str__(self):
        return (
            f"{self.get_recommendation_type_display()} recommendation "
            f"{self.public_id}"
        )

    def clean(self):
        super().clean()

        if (
            self.referred_user_id
            and self.referrer_id == self.referred_user_id
        ):
            raise ValidationError(
                {"referred_user": "A Majestian cannot recommend themselves."}
            )

        if self.reward_percentage_snapshot > 100:
            raise ValidationError(
                {
                    "reward_percentage_snapshot":
                    "Reward percentage cannot exceed 100%."
                }
            )
