#!/usr/bin/env bash

set -Eeuo pipefail

###############################################################################
# MAJICMALL MEGAVERSE
# OPERATION: MAJESTIAN ECONOMY CORE
#
# Installer 1:
#   - MajesticCoinSettings
#   - CitizenLevelReward
#   - MajestianWallet
#   - CoinTransaction
#   - EconomyEngine service
#   - Automatic wallet creation
#   - Admin integration
#   - Default economic settings and citizen levels
###############################################################################

PROJECT_ROOT="$(pwd)"
APP_NAME="majestian_economy"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_ROOT="${PROJECT_ROOT}/backups/${APP_NAME}_${TIMESTAMP}"

echo
echo "=============================================================="
echo "  MAJICMALL MEGAVERSE"
echo "  OPERATION: MAJESTIAN ECONOMY CORE"
echo "=============================================================="
echo

###############################################################################
# 1. VERIFY PROJECT
###############################################################################

if [[ ! -f "${PROJECT_ROOT}/manage.py" ]]; then
    echo "ERROR: manage.py was not found."
    echo "Run this installer from the Django project root."
    exit 1
fi

PYTHON_BIN="python"

if [[ -x "${PROJECT_ROOT}/.venv/bin/python" ]]; then
    PYTHON_BIN="${PROJECT_ROOT}/.venv/bin/python"
elif [[ -x "${PROJECT_ROOT}/venv/bin/python" ]]; then
    PYTHON_BIN="${PROJECT_ROOT}/venv/bin/python"
fi

echo "Project root: ${PROJECT_ROOT}"
echo "Python:       ${PYTHON_BIN}"
echo "Backup:       ${BACKUP_ROOT}"
echo

"${PYTHON_BIN}" - <<'PY'
import django
print(f"Django version: {django.get_version()}")
PY

###############################################################################
# 2. DETECT DJANGO SETTINGS MODULE
###############################################################################

SETTINGS_MODULE="$("${PYTHON_BIN}" - <<'PY'
import re
from pathlib import Path

text = Path("manage.py").read_text(encoding="utf-8")

match = re.search(
    r"DJANGO_SETTINGS_MODULE[\"']?\s*,\s*[\"']([^\"']+)[\"']",
    text,
)

if not match:
    match = re.search(
        r"DJANGO_SETTINGS_MODULE[\"']?\]\s*=\s*[\"']([^\"']+)[\"']",
        text,
    )

if not match:
    match = re.search(
        r"setdefault\(\s*[\"']DJANGO_SETTINGS_MODULE[\"']\s*,\s*[\"']([^\"']+)",
        text,
    )

if not match:
    raise SystemExit("Could not detect DJANGO_SETTINGS_MODULE from manage.py")

print(match.group(1))
PY
)"

SETTINGS_FILE="${PROJECT_ROOT}/${SETTINGS_MODULE//./\/}.py"

if [[ ! -f "${SETTINGS_FILE}" ]]; then
    echo "ERROR: Detected settings file does not exist:"
    echo "${SETTINGS_FILE}"
    exit 1
fi

echo "Settings module: ${SETTINGS_MODULE}"
echo "Settings file:   ${SETTINGS_FILE}"
echo

###############################################################################
# 3. BACKUP
###############################################################################

mkdir -p "${BACKUP_ROOT}"

cp "${SETTINGS_FILE}" "${BACKUP_ROOT}/settings.py.before"

if [[ -d "${PROJECT_ROOT}/${APP_NAME}" ]]; then
    cp -a "${PROJECT_ROOT}/${APP_NAME}" "${BACKUP_ROOT}/${APP_NAME}.before"
fi

if [[ -f "${PROJECT_ROOT}/db.sqlite3" ]]; then
    cp "${PROJECT_ROOT}/db.sqlite3" "${BACKUP_ROOT}/db.sqlite3.before"
    echo "SQLite database backup created."
else
    echo "External database detected or db.sqlite3 is not present."
    echo "Code backup will continue; database backup is managed by the provider."
fi

echo "Backup complete."
echo

###############################################################################
# 4. CREATE APPLICATION STRUCTURE
###############################################################################

mkdir -p "${PROJECT_ROOT}/${APP_NAME}/migrations"
mkdir -p "${PROJECT_ROOT}/${APP_NAME}/management/commands"
mkdir -p "${PROJECT_ROOT}/${APP_NAME}/templatetags"

touch "${PROJECT_ROOT}/${APP_NAME}/__init__.py"
touch "${PROJECT_ROOT}/${APP_NAME}/migrations/__init__.py"
touch "${PROJECT_ROOT}/${APP_NAME}/management/__init__.py"
touch "${PROJECT_ROOT}/${APP_NAME}/management/commands/__init__.py"
touch "${PROJECT_ROOT}/${APP_NAME}/templatetags/__init__.py"

###############################################################################
# 5. APPS.PY
###############################################################################

cat > "${PROJECT_ROOT}/${APP_NAME}/apps.py" <<'PY'
from django.apps import AppConfig


class MajestianEconomyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "majestian_economy"
    verbose_name = "Majestic Economy"

    def ready(self):
        # Importing these modules activates wallet signals, seed data,
        # and Majestic Economy system checks.
        from . import checks  # noqa: F401
        from . import signals  # noqa: F401
PY

###############################################################################
# 6. MODELS
###############################################################################

cat > "${PROJECT_ROOT}/${APP_NAME}/models.py" <<'PY'
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
PY

###############################################################################
# 7. ECONOMY SERVICE
###############################################################################

cat > "${PROJECT_ROOT}/${APP_NAME}/services.py" <<'PY'
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from .models import (
    CitizenLevelReward,
    CoinTransaction,
    MajesticCoinSettings,
    MajestianRecommendation,
    MajestianWallet,
)


COIN_QUANTIZER = Decimal("0.01")
MONEY_QUANTIZER = Decimal("0.01")
PERCENT_DIVISOR = Decimal("100")


@dataclass(frozen=True)
class ReferralCalculation:
    membership_amount: Decimal
    referral_percentage: Decimal
    reward_value: Decimal
    coin_value: Decimal
    coins_awarded: Decimal


class EconomyEngine:
    """
    Central service for all Majestic Coin calculations and ledger activity.

    Views, checkout systems, admin actions, subscriptions, creator tools,
    advertising systems, and future AI executives should call this service
    instead of updating wallet balances directly.
    """

    @staticmethod
    def decimal(value: Any) -> Decimal:
        try:
            return Decimal(str(value))
        except Exception as exc:
            raise ValidationError(f"Invalid decimal value: {value}") from exc

    @classmethod
    def economy_settings(cls) -> MajesticCoinSettings:
        return MajesticCoinSettings.load()

    @classmethod
    def coins_from_value(
        cls,
        platform_value: Decimal | str | int | float,
    ) -> Decimal:
        settings_obj = cls.economy_settings()
        value = cls.decimal(platform_value)

        if value < 0:
            raise ValidationError("Platform value cannot be negative.")

        if settings_obj.coin_value <= 0:
            raise ValidationError("Majestic Coin value must be greater than zero.")

        return (
            value / settings_obj.coin_value
        ).quantize(COIN_QUANTIZER, rounding=ROUND_HALF_UP)

    @classmethod
    def value_from_coins(
        cls,
        coin_amount: Decimal | str | int | float,
    ) -> Decimal:
        settings_obj = cls.economy_settings()
        coins = cls.decimal(coin_amount)

        if coins < 0:
            raise ValidationError("Coin amount cannot be negative.")

        return (
            coins * settings_obj.coin_value
        ).quantize(MONEY_QUANTIZER, rounding=ROUND_HALF_UP)

    @classmethod
    def calculate_referral(
        cls,
        membership_amount: Decimal | str | int | float,
        referral_percentage: Decimal | str | int | float,
    ) -> ReferralCalculation:
        settings_obj = cls.economy_settings()

        amount = cls.decimal(membership_amount).quantize(
            MONEY_QUANTIZER,
            rounding=ROUND_HALF_UP,
        )
        percentage = cls.decimal(referral_percentage)

        if amount < 0:
            raise ValidationError("Membership amount cannot be negative.")

        if percentage < 0 or percentage > 100:
            raise ValidationError(
                "Referral percentage must be between 0 and 100."
            )

        reward_value = (
            amount * percentage / PERCENT_DIVISOR
        ).quantize(MONEY_QUANTIZER, rounding=ROUND_HALF_UP)

        coins_awarded = (
            reward_value / settings_obj.coin_value
        ).quantize(COIN_QUANTIZER, rounding=ROUND_HALF_UP)

        return ReferralCalculation(
            membership_amount=amount,
            referral_percentage=percentage,
            reward_value=reward_value,
            coin_value=settings_obj.coin_value,
            coins_awarded=coins_awarded,
        )

    @classmethod
    def wallet_for_user(
        cls,
        user,
        *,
        lock: bool = False,
    ) -> MajestianWallet:
        queryset = MajestianWallet.objects

        if lock:
            queryset = queryset.select_for_update()

        try:
            return queryset.get(user=user)
        except MajestianWallet.DoesNotExist:
            try:
                return MajestianWallet.objects.create(user=user)
            except IntegrityError:
                return queryset.get(user=user)

    @classmethod
    @transaction.atomic
    def create_credit(
        cls,
        *,
        user,
        coin_amount: Decimal | str | int | float,
        transaction_type: str,
        description: str,
        status: str = CoinTransaction.Status.POSTED,
        reference_type: str = "",
        reference_id: str = "",
        idempotency_key: str | None = None,
        metadata: dict | None = None,
        available_at=None,
    ) -> CoinTransaction:
        coins = cls.decimal(coin_amount).quantize(
            COIN_QUANTIZER,
            rounding=ROUND_HALF_UP,
        )

        if coins <= 0:
            raise ValidationError("Credit amount must be greater than zero.")

        if idempotency_key:
            existing = CoinTransaction.objects.filter(
                idempotency_key=idempotency_key
            ).first()

            if existing:
                return existing

        settings_obj = cls.economy_settings()
        wallet = cls.wallet_for_user(user, lock=True)

        if wallet.status != MajestianWallet.Status.ACTIVE:
            raise ValidationError(
                "This Majestian Wallet is not active."
            )

        platform_value = (
            coins * settings_obj.coin_value
        ).quantize(MONEY_QUANTIZER, rounding=ROUND_HALF_UP)

        now = timezone.now()

        if status == CoinTransaction.Status.POSTED:
            posted_at = now
        else:
            posted_at = None

        ledger_entry = CoinTransaction.objects.create(
            wallet=wallet,
            transaction_type=transaction_type,
            direction=CoinTransaction.Direction.CREDIT,
            status=status,
            coin_amount=coins,
            coin_value_snapshot=settings_obj.coin_value,
            platform_value=platform_value,
            description=description,
            reference_type=reference_type,
            reference_id=str(reference_id or ""),
            idempotency_key=idempotency_key,
            metadata=metadata or {},
            available_at=available_at,
            posted_at=posted_at,
        )

        if status == CoinTransaction.Status.POSTED:
            MajestianWallet.objects.filter(pk=wallet.pk).update(
                available_coins=F("available_coins") + coins,
                lifetime_earned_coins=F("lifetime_earned_coins") + coins,
                last_transaction_at=now,
            )

        elif status == CoinTransaction.Status.PENDING:
            MajestianWallet.objects.filter(pk=wallet.pk).update(
                pending_coins=F("pending_coins") + coins,
                last_transaction_at=now,
            )

        return ledger_entry

    @classmethod
    @transaction.atomic
    def create_debit(
        cls,
        *,
        user,
        coin_amount: Decimal | str | int | float,
        transaction_type: str,
        description: str,
        reference_type: str = "",
        reference_id: str = "",
        idempotency_key: str | None = None,
        metadata: dict | None = None,
    ) -> CoinTransaction:
        coins = cls.decimal(coin_amount).quantize(
            COIN_QUANTIZER,
            rounding=ROUND_HALF_UP,
        )

        if coins <= 0:
            raise ValidationError("Debit amount must be greater than zero.")

        if idempotency_key:
            existing = CoinTransaction.objects.filter(
                idempotency_key=idempotency_key
            ).first()

            if existing:
                return existing

        settings_obj = cls.economy_settings()
        wallet = cls.wallet_for_user(user, lock=True)
        wallet.refresh_from_db()

        if wallet.status != MajestianWallet.Status.ACTIVE:
            raise ValidationError(
                "This Majestian Wallet is not active."
            )

        if wallet.available_coins < coins:
            raise ValidationError("Insufficient Majestic Coin balance.")

        platform_value = (
            coins * settings_obj.coin_value
        ).quantize(MONEY_QUANTIZER, rounding=ROUND_HALF_UP)

        now = timezone.now()

        ledger_entry = CoinTransaction.objects.create(
            wallet=wallet,
            transaction_type=transaction_type,
            direction=CoinTransaction.Direction.DEBIT,
            status=CoinTransaction.Status.POSTED,
            coin_amount=coins,
            coin_value_snapshot=settings_obj.coin_value,
            platform_value=platform_value,
            description=description,
            reference_type=reference_type,
            reference_id=str(reference_id or ""),
            idempotency_key=idempotency_key,
            metadata=metadata or {},
            posted_at=now,
        )

        updates = {
            "available_coins": F("available_coins") - coins,
            "last_transaction_at": now,
        }

        if transaction_type == CoinTransaction.TransactionType.REDEMPTION:
            updates["lifetime_redeemed_coins"] = (
                F("lifetime_redeemed_coins") + coins
            )

        MajestianWallet.objects.filter(pk=wallet.pk).update(**updates)

        return ledger_entry

    @classmethod
    @transaction.atomic
    def post_pending_transaction(
        cls,
        ledger_entry: CoinTransaction,
    ) -> CoinTransaction:
        entry = (
            CoinTransaction.objects
            .select_for_update()
            .select_related("wallet")
            .get(pk=ledger_entry.pk)
        )

        if entry.status == CoinTransaction.Status.POSTED:
            return entry

        if entry.status != CoinTransaction.Status.PENDING:
            raise ValidationError(
                "Only pending transactions can be posted."
            )

        if entry.available_at and entry.available_at > timezone.now():
            raise ValidationError(
                "This reward is still within its holding period."
            )

        wallet = MajestianWallet.objects.select_for_update().get(
            pk=entry.wallet_id
        )

        if wallet.pending_coins < entry.coin_amount:
            raise ValidationError(
                "Wallet pending balance is lower than the transaction amount."
            )

        now = timezone.now()

        MajestianWallet.objects.filter(pk=wallet.pk).update(
            pending_coins=F("pending_coins") - entry.coin_amount,
            available_coins=F("available_coins") + entry.coin_amount,
            lifetime_earned_coins=(
                F("lifetime_earned_coins") + entry.coin_amount
            ),
            last_transaction_at=now,
        )

        entry.status = CoinTransaction.Status.POSTED
        entry.posted_at = now
        entry.save(update_fields=("status", "posted_at", "updated_at"))

        return entry

    @classmethod
    @transaction.atomic
    def reverse_transaction(
        cls,
        ledger_entry: CoinTransaction,
        *,
        reason: str,
        idempotency_key: str | None = None,
    ) -> CoinTransaction:
        original = (
            CoinTransaction.objects
            .select_for_update()
            .select_related("wallet", "wallet__user")
            .get(pk=ledger_entry.pk)
        )

        if original.status == CoinTransaction.Status.REVERSED:
            try:
                return original.reversal_transaction
            except CoinTransaction.DoesNotExist:
                raise ValidationError(
                    "The transaction is marked reversed but has no reversal entry."
                )

        if original.status != CoinTransaction.Status.POSTED:
            raise ValidationError(
                "Only posted transactions can be reversed."
            )

        wallet = MajestianWallet.objects.select_for_update().get(
            pk=original.wallet_id
        )

        now = timezone.now()

        if original.direction == CoinTransaction.Direction.CREDIT:
            if wallet.available_coins < original.coin_amount:
                raise ValidationError(
                    "The wallet no longer contains enough available coins "
                    "to reverse this credit."
                )

            reversal_direction = CoinTransaction.Direction.DEBIT

            MajestianWallet.objects.filter(pk=wallet.pk).update(
                available_coins=F("available_coins") - original.coin_amount,
                lifetime_reversed_coins=(
                    F("lifetime_reversed_coins") + original.coin_amount
                ),
                last_transaction_at=now,
            )

        else:
            reversal_direction = CoinTransaction.Direction.CREDIT

            MajestianWallet.objects.filter(pk=wallet.pk).update(
                available_coins=F("available_coins") + original.coin_amount,
                last_transaction_at=now,
            )

        reversal = CoinTransaction.objects.create(
            wallet=wallet,
            transaction_type=CoinTransaction.TransactionType.REVERSAL,
            direction=reversal_direction,
            status=CoinTransaction.Status.POSTED,
            coin_amount=original.coin_amount,
            coin_value_snapshot=original.coin_value_snapshot,
            platform_value=original.platform_value,
            description=f"Reversal: {reason}",
            reference_type="CoinTransaction",
            reference_id=str(original.public_id),
            idempotency_key=idempotency_key,
            metadata={
                "original_transaction": str(original.public_id),
                "reason": reason,
            },
            posted_at=now,
            reversal_of=original,
        )

        original.status = CoinTransaction.Status.REVERSED
        original.reversed_at = now
        original.save(
            update_fields=("status", "reversed_at", "updated_at")
        )

        return reversal

    @classmethod
    @transaction.atomic
    def award_recommendation(
        cls,
        recommendation: MajestianRecommendation,
        *,
        place_on_hold: bool | None = None,
    ) -> CoinTransaction:
        recommendation = (
            MajestianRecommendation.objects
            .select_for_update()
            .select_related("referrer", "citizen_level")
            .get(pk=recommendation.pk)
        )

        if recommendation.reward_transaction_id:
            return recommendation.reward_transaction

        economy = cls.economy_settings()

        if not economy.referral_rewards_enabled:
            raise ValidationError(
                "Majestian recommendation rewards are currently disabled."
            )

        if recommendation.fraud_review_required:
            raise ValidationError(
                "This recommendation requires administrator review."
            )

        if economy.require_payment_confirmation:
            allowed_statuses = {
                MajestianRecommendation.Status.PAYMENT_CONFIRMED,
                MajestianRecommendation.Status.REWARD_PENDING,
            }

            if recommendation.status not in allowed_statuses:
                raise ValidationError(
                    "Payment must be confirmed before issuing the reward."
                )

        percentage = recommendation.reward_percentage_snapshot

        if percentage <= 0 and recommendation.citizen_level_id:
            percentage = recommendation.citizen_level.referral_percentage

        calculation = cls.calculate_referral(
            recommendation.membership_amount,
            percentage,
        )

        if place_on_hold is None:
            place_on_hold = economy.reward_hold_days > 0

        if place_on_hold:
            ledger_status = CoinTransaction.Status.PENDING
            available_at = timezone.now() + timedelta(
                days=economy.reward_hold_days
            )
            recommendation_status = (
                MajestianRecommendation.Status.REWARD_PENDING
            )
        else:
            ledger_status = CoinTransaction.Status.POSTED
            available_at = None
            recommendation_status = MajestianRecommendation.Status.REWARDED

        ledger_entry = cls.create_credit(
            user=recommendation.referrer,
            coin_amount=calculation.coins_awarded,
            transaction_type=(
                CoinTransaction.TransactionType.CITIZEN_REFERRAL
            ),
            description=(
                f"{recommendation.get_recommendation_type_display()} "
                f"recommendation reward"
            ),
            status=ledger_status,
            reference_type="MajestianRecommendation",
            reference_id=str(recommendation.public_id),
            idempotency_key=(
                f"recommendation:{recommendation.public_id}"
            ),
            metadata={
                "membership_name": recommendation.membership_name,
                "membership_amount": str(calculation.membership_amount),
                "reward_percentage": str(calculation.referral_percentage),
                "reward_value": str(calculation.reward_value),
                "coin_value": str(calculation.coin_value),
            },
            available_at=available_at,
        )

        recommendation.reward_percentage_snapshot = (
            calculation.referral_percentage
        )
        recommendation.reward_value = calculation.reward_value
        recommendation.coins_awarded = calculation.coins_awarded
        recommendation.reward_transaction = ledger_entry
        recommendation.status = recommendation_status

        if ledger_status == CoinTransaction.Status.POSTED:
            recommendation.rewarded_at = timezone.now()

        recommendation.save(
            update_fields=(
                "reward_percentage_snapshot",
                "reward_value",
                "coins_awarded",
                "reward_transaction",
                "status",
                "rewarded_at",
                "updated_at",
            )
        )

        return ledger_entry

    @classmethod
    def award_referral(
        cls,
        *,
        referrer,
        membership_amount,
        citizen_level: CitizenLevelReward,
        membership_name: str = "",
        referred_user=None,
        payment_reference: str = "",
        payment_confirmed: bool = True,
        place_on_hold: bool | None = None,
        metadata: dict | None = None,
    ) -> MajestianRecommendation:
        status = (
            MajestianRecommendation.Status.PAYMENT_CONFIRMED
            if payment_confirmed
            else MajestianRecommendation.Status.PENDING_PAYMENT
        )

        recommendation = MajestianRecommendation.objects.create(
            referrer=referrer,
            referred_user=referred_user,
            recommendation_type=(
                MajestianRecommendation.RecommendationType.CITIZEN
            ),
            citizen_level=citizen_level,
            membership_name=membership_name,
            membership_amount=membership_amount,
            reward_percentage_snapshot=(
                citizen_level.referral_percentage
            ),
            status=status,
            payment_reference=payment_reference,
            payment_confirmed_at=(
                timezone.now() if payment_confirmed else None
            ),
            metadata=metadata or {},
        )

        if payment_confirmed:
            cls.award_recommendation(
                recommendation,
                place_on_hold=place_on_hold,
            )
            recommendation.refresh_from_db()

        return recommendation
PY

###############################################################################
# 8. SIGNALS AND DEFAULT DATA
###############################################################################

cat > "${PROJECT_ROOT}/${APP_NAME}/signals.py" <<'PY'
from decimal import Decimal

from django.apps import apps
from django.conf import settings
from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver

from .models import (
    CitizenLevelReward,
    MajesticCoinSettings,
    MajestianWallet,
)


@receiver(
    post_save,
    sender=settings.AUTH_USER_MODEL,
    dispatch_uid="majestian_economy_create_wallet",
)
def create_majestian_wallet(sender, instance, created, **kwargs):
    if created:
        MajestianWallet.objects.get_or_create(user=instance)


@receiver(
    post_migrate,
    dispatch_uid="majestian_economy_seed_defaults",
)
def seed_majestian_economy_defaults(sender, app_config=None, **kwargs):
    if app_config and app_config.label != "majestian_economy":
        return

    if not apps.is_installed("majestian_economy"):
        return

    MajesticCoinSettings.objects.get_or_create(
        pk=1,
        defaults={
            "coin_name": "Majestic Coin",
            "coin_symbol": "MC",
            "currency_code": "USD",
            "coin_value": Decimal("0.1000"),
            "minimum_redemption_coins": Decimal("100.00"),
            "maximum_daily_redemption_coins": Decimal("5000.00"),
            "reward_hold_days": 7,
        },
    )

    default_levels = (
        {
            "name": "Vision",
            "slug": "vision",
            "referral_percentage": Decimal("10.000"),
            "display_order": 10,
            "description": (
                "Vision Majestian recommendation reward level."
            ),
        },
        {
            "name": "Pro",
            "slug": "pro",
            "referral_percentage": Decimal("12.000"),
            "display_order": 20,
            "description": (
                "Pro Majestian recommendation reward level."
            ),
        },
        {
            "name": "Elite",
            "slug": "elite",
            "referral_percentage": Decimal("15.000"),
            "display_order": 30,
            "description": (
                "Elite Majestian recommendation reward level."
            ),
        },
        {
            "name": "Majestic",
            "slug": "majestic",
            "referral_percentage": Decimal("20.000"),
            "display_order": 40,
            "description": (
                "Majestic Majestian recommendation reward level."
            ),
        },
    )

    for level in default_levels:
        CitizenLevelReward.objects.update_or_create(
            slug=level["slug"],
            defaults=level,
        )
PY

###############################################################################
# 9. SYSTEM CHECKS
###############################################################################

cat > "${PROJECT_ROOT}/${APP_NAME}/checks.py" <<'PY'
from django.core.checks import Error, register
from django.db.utils import OperationalError, ProgrammingError

from .models import MajesticCoinSettings


@register()
def majestic_economy_checks(app_configs, **kwargs):
    errors = []

    try:
        settings_obj = MajesticCoinSettings.objects.filter(pk=1).first()
    except (OperationalError, ProgrammingError):
        # Database tables may not exist yet during the first migration.
        return errors

    if settings_obj and settings_obj.coin_value <= 0:
        errors.append(
            Error(
                "Majestic Coin value must be greater than zero.",
                hint=(
                    "Open Majestic Economy settings in Django Admin and "
                    "enter a positive coin value."
                ),
                id="majestian_economy.E001",
            )
        )

    return errors
PY

###############################################################################
# 10. ADMIN
###############################################################################

cat > "${PROJECT_ROOT}/${APP_NAME}/admin.py" <<'PY'
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db.models import Count, Sum
from django.utils.html import format_html

from .models import (
    CitizenLevelReward,
    CoinTransaction,
    MajesticCoinSettings,
    MajestianRecommendation,
    MajestianWallet,
)
from .services import EconomyEngine


@admin.register(MajesticCoinSettings)
class MajesticCoinSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        (
            "Majestic Coin Identity",
            {
                "fields": (
                    "coin_name",
                    "coin_symbol",
                    "currency_code",
                    "coin_value",
                    "is_active",
                )
            },
        ),
        (
            "Redemption Policy",
            {
                "fields": (
                    "minimum_redemption_coins",
                    "maximum_daily_redemption_coins",
                    "redemption_enabled",
                )
            },
        ),
        (
            "Reward Programs",
            {
                "fields": (
                    "referral_rewards_enabled",
                    "merchant_rewards_enabled",
                    "creator_rewards_enabled",
                    "purchase_rewards_enabled",
                    "bonus_events_enabled",
                )
            },
        ),
        (
            "Reward Protection",
            {
                "fields": (
                    "require_payment_confirmation",
                    "reward_hold_days",
                )
            },
        ),
        (
            "Audit",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    readonly_fields = ("created_at", "updated_at")

    def has_add_permission(self, request):
        return not MajesticCoinSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CitizenLevelReward)
class CitizenLevelRewardAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "referral_percentage_display",
        "display_order",
        "is_active",
        "updated_at",
    )
    list_editable = (
        "display_order",
        "is_active",
    )
    list_filter = ("is_active",)
    search_fields = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("display_order", "name")

    @admin.display(description="Referral reward", ordering="referral_percentage")
    def referral_percentage_display(self, obj):
        return f"{obj.referral_percentage}%"


@admin.register(MajestianWallet)
class MajestianWalletAdmin(admin.ModelAdmin):
    list_display = (
        "wallet_owner",
        "status",
        "available_balance",
        "pending_balance",
        "platform_value_display",
        "lifetime_earned_coins",
        "opportunity_score",
        "last_transaction_at",
    )
    list_filter = ("status", "created_at", "last_transaction_at")
    search_fields = (
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
    )
    readonly_fields = (
        "user",
        "available_coins",
        "pending_coins",
        "lifetime_earned_coins",
        "lifetime_redeemed_coins",
        "lifetime_reversed_coins",
        "lifetime_expired_coins",
        "last_transaction_at",
        "created_at",
        "updated_at",
        "platform_value_detail",
    )

    fieldsets = (
        (
            "Majestian",
            {
                "fields": (
                    "user",
                    "status",
                    "opportunity_score",
                )
            },
        ),
        (
            "Current Balances",
            {
                "fields": (
                    "available_coins",
                    "pending_coins",
                    "platform_value_detail",
                )
            },
        ),
        (
            "Lifetime Activity",
            {
                "fields": (
                    "lifetime_earned_coins",
                    "lifetime_redeemed_coins",
                    "lifetime_reversed_coins",
                    "lifetime_expired_coins",
                )
            },
        ),
        (
            "Audit",
            {
                "fields": (
                    "last_transaction_at",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    actions = None

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Majestian", ordering="user__first_name")
    def wallet_owner(self, obj):
        full_name = obj.user.get_full_name().strip()
        return full_name or obj.user.get_username()

    @admin.display(description="Available MC", ordering="available_coins")
    def available_balance(self, obj):
        return f"{obj.available_coins:,.2f} MC"

    @admin.display(description="Pending MC", ordering="pending_coins")
    def pending_balance(self, obj):
        return f"{obj.pending_coins:,.2f} MC"

    @admin.display(description="Platform value")
    def platform_value_display(self, obj):
        return f"${obj.available_platform_value:,.2f}"

    @admin.display(description="Current platform value")
    def platform_value_detail(self, obj):
        return format_html(
            "<strong>{}</strong> available + "
            "<strong>{}</strong> pending",
            f"${obj.available_platform_value:,.2f}",
            f"${obj.pending_platform_value:,.2f}",
        )


@admin.register(CoinTransaction)
class CoinTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "short_public_id",
        "wallet_owner",
        "transaction_type",
        "direction",
        "status",
        "coin_amount_display",
        "platform_value_display",
        "created_at",
    )
    list_filter = (
        "status",
        "direction",
        "transaction_type",
        "created_at",
    )
    search_fields = (
        "public_id",
        "wallet__user__username",
        "wallet__user__email",
        "wallet__user__first_name",
        "wallet__user__last_name",
        "description",
        "reference_id",
        "idempotency_key",
    )
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    actions = (
        "post_selected_pending_rewards",
    )

    readonly_fields = (
        "public_id",
        "wallet",
        "transaction_type",
        "direction",
        "status",
        "coin_amount",
        "coin_value_snapshot",
        "platform_value",
        "description",
        "reference_type",
        "reference_id",
        "idempotency_key",
        "metadata",
        "available_at",
        "posted_at",
        "reversed_at",
        "reversal_of",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            "Transaction",
            {
                "fields": (
                    "public_id",
                    "wallet",
                    "transaction_type",
                    "direction",
                    "status",
                    "description",
                )
            },
        ),
        (
            "Value",
            {
                "fields": (
                    "coin_amount",
                    "coin_value_snapshot",
                    "platform_value",
                )
            },
        ),
        (
            "Reference",
            {
                "fields": (
                    "reference_type",
                    "reference_id",
                    "idempotency_key",
                    "reversal_of",
                )
            },
        ),
        (
            "Timing",
            {
                "fields": (
                    "available_at",
                    "posted_at",
                    "reversed_at",
                    "created_at",
                    "updated_at",
                )
            },
        ),
        (
            "Metadata",
            {
                "fields": ("metadata",),
                "classes": ("collapse",),
            },
        ),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.method in ("GET", "HEAD", "OPTIONS")

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="ID")
    def short_public_id(self, obj):
        return str(obj.public_id)[:8]

    @admin.display(description="Majestian")
    def wallet_owner(self, obj):
        full_name = obj.wallet.user.get_full_name().strip()
        return full_name or obj.wallet.user.get_username()

    @admin.display(description="Coins", ordering="coin_amount")
    def coin_amount_display(self, obj):
        sign = "+" if obj.direction == obj.Direction.CREDIT else "-"
        return f"{sign}{obj.coin_amount:,.2f} MC"

    @admin.display(description="Value", ordering="platform_value")
    def platform_value_display(self, obj):
        return f"${obj.platform_value:,.2f}"

    @admin.action(description="Post selected eligible pending rewards")
    def post_selected_pending_rewards(self, request, queryset):
        posted = 0
        skipped = 0

        for entry in queryset.filter(status=CoinTransaction.Status.PENDING):
            try:
                EconomyEngine.post_pending_transaction(entry)
                posted += 1
            except ValidationError:
                skipped += 1

        if posted:
            self.message_user(
                request,
                f"{posted} pending reward(s) posted.",
                level=messages.SUCCESS,
            )

        if skipped:
            self.message_user(
                request,
                f"{skipped} reward(s) were not yet eligible.",
                level=messages.WARNING,
            )

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        totals = CoinTransaction.objects.filter(
            status=CoinTransaction.Status.POSTED,
            direction=CoinTransaction.Direction.CREDIT,
        ).aggregate(
            total_coins=Sum("coin_amount"),
            total_value=Sum("platform_value"),
        )

        extra_context["economy_total_coins"] = (
            totals["total_coins"] or 0
        )
        extra_context["economy_total_value"] = (
            totals["total_value"] or 0
        )

        return super().changelist_view(
            request,
            extra_context=extra_context,
        )


@admin.register(MajestianRecommendation)
class MajestianRecommendationAdmin(admin.ModelAdmin):
    list_display = (
        "short_public_id",
        "referrer_name",
        "referred_name",
        "recommendation_type",
        "citizen_level",
        "membership_amount_display",
        "reward_percentage_display",
        "coins_awarded_display",
        "status",
        "created_at",
    )
    list_filter = (
        "status",
        "recommendation_type",
        "citizen_level",
        "fraud_review_required",
        "created_at",
    )
    search_fields = (
        "public_id",
        "referrer__username",
        "referrer__email",
        "referrer__first_name",
        "referrer__last_name",
        "referred_user__username",
        "referred_user__email",
        "membership_name",
        "payment_reference",
        "referral_code",
    )
    autocomplete_fields = (
        "referrer",
        "referred_user",
        "citizen_level",
    )
    readonly_fields = (
        "public_id",
        "reward_percentage_snapshot",
        "reward_value",
        "coins_awarded",
        "reward_transaction",
        "rewarded_at",
        "created_at",
        "updated_at",
    )
    actions = (
        "issue_selected_recommendation_rewards",
    )

    fieldsets = (
        (
            "Recommendation",
            {
                "fields": (
                    "public_id",
                    "referrer",
                    "referred_user",
                    "recommendation_type",
                    "citizen_level",
                    "referral_code",
                )
            },
        ),
        (
            "Membership and Payment",
            {
                "fields": (
                    "membership_name",
                    "membership_amount",
                    "payment_reference",
                    "payment_confirmed_at",
                )
            },
        ),
        (
            "Reward",
            {
                "fields": (
                    "reward_percentage_snapshot",
                    "reward_value",
                    "coins_awarded",
                    "reward_transaction",
                    "rewarded_at",
                )
            },
        ),
        (
            "Review",
            {
                "fields": (
                    "status",
                    "fraud_review_required",
                    "fraud_review_notes",
                    "administrator_notes",
                )
            },
        ),
        (
            "Metadata",
            {
                "fields": (
                    "metadata",
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(description="ID")
    def short_public_id(self, obj):
        return str(obj.public_id)[:8]

    @admin.display(description="Referrer")
    def referrer_name(self, obj):
        name = obj.referrer.get_full_name().strip()
        return name or obj.referrer.get_username()

    @admin.display(description="New Majestian")
    def referred_name(self, obj):
        if not obj.referred_user:
            return "Not connected"

        name = obj.referred_user.get_full_name().strip()
        return name or obj.referred_user.get_username()

    @admin.display(description="Membership")
    def membership_amount_display(self, obj):
        return f"${obj.membership_amount:,.2f}"

    @admin.display(description="Reward %")
    def reward_percentage_display(self, obj):
        return f"{obj.reward_percentage_snapshot}%"

    @admin.display(description="Coins")
    def coins_awarded_display(self, obj):
        return f"{obj.coins_awarded:,.2f} MC"

    @admin.action(description="Issue rewards for selected recommendations")
    def issue_selected_recommendation_rewards(self, request, queryset):
        rewarded = 0
        skipped = 0

        for recommendation in queryset:
            try:
                EconomyEngine.award_recommendation(recommendation)
                rewarded += 1
            except ValidationError:
                skipped += 1

        if rewarded:
            self.message_user(
                request,
                f"{rewarded} recommendation reward(s) created.",
                level=messages.SUCCESS,
            )

        if skipped:
            self.message_user(
                request,
                f"{skipped} recommendation(s) could not be rewarded.",
                level=messages.WARNING,
            )
PY

###############################################################################
# 11. MANAGEMENT COMMAND: ECONOMY STATUS
###############################################################################

cat > "${PROJECT_ROOT}/${APP_NAME}/management/commands/majestian_economy_status.py" <<'PY'
from django.core.management.base import BaseCommand
from django.db.models import Sum

from majestian_economy.models import (
    CitizenLevelReward,
    CoinTransaction,
    MajesticCoinSettings,
    MajestianWallet,
)


class Command(BaseCommand):
    help = "Display the current Majestian Economy configuration and totals."

    def handle(self, *args, **options):
        settings_obj = MajesticCoinSettings.load()

        wallets = MajestianWallet.objects.count()

        available = (
            MajestianWallet.objects.aggregate(total=Sum("available_coins"))[
                "total"
            ]
            or 0
        )

        pending = (
            MajestianWallet.objects.aggregate(total=Sum("pending_coins"))[
                "total"
            ]
            or 0
        )

        posted_transactions = CoinTransaction.objects.filter(
            status=CoinTransaction.Status.POSTED
        ).count()

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS("MAJESTIAN ECONOMY STATUS")
        )
        self.stdout.write("=" * 55)
        self.stdout.write(
            f"Coin standard: 1 {settings_obj.coin_symbol} "
            f"= ${settings_obj.coin_value}"
        )
        self.stdout.write(f"Currency:      {settings_obj.currency_code}")
        self.stdout.write(f"Wallets:       {wallets}")
        self.stdout.write(f"Available MC:  {available}")
        self.stdout.write(f"Pending MC:    {pending}")
        self.stdout.write(f"Posted ledger: {posted_transactions}")
        self.stdout.write("")
        self.stdout.write("Citizen Levels:")

        for level in CitizenLevelReward.objects.order_by(
            "display_order",
            "name",
        ):
            active = "Active" if level.is_active else "Inactive"
            self.stdout.write(
                f"  - {level.name}: "
                f"{level.referral_percentage}% ({active})"
            )

        self.stdout.write("")
PY

###############################################################################
# 12. MANAGEMENT COMMAND: POST ELIGIBLE REWARDS
###############################################################################

cat > "${PROJECT_ROOT}/${APP_NAME}/management/commands/post_eligible_coin_rewards.py" <<'PY'
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.utils import timezone

from majestian_economy.models import CoinTransaction
from majestian_economy.services import EconomyEngine


class Command(BaseCommand):
    help = "Post pending Majestic Coin rewards whose holding period has ended."

    def handle(self, *args, **options):
        eligible = CoinTransaction.objects.filter(
            status=CoinTransaction.Status.PENDING,
            direction=CoinTransaction.Direction.CREDIT,
            available_at__lte=timezone.now(),
        ).order_by("available_at", "id")

        posted = 0
        skipped = 0

        for entry in eligible.iterator():
            try:
                EconomyEngine.post_pending_transaction(entry)
                posted += 1
            except ValidationError as exc:
                skipped += 1
                self.stderr.write(
                    f"Skipped {entry.public_id}: {exc}"
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Posted {posted} eligible Majestic Coin reward(s)."
            )
        )

        if skipped:
            self.stdout.write(
                self.style.WARNING(
                    f"Skipped {skipped} reward(s)."
                )
            )
PY

###############################################################################
# 13. TEMPLATE TAGS FOR FUTURE DASHBOARDS
###############################################################################

cat > "${PROJECT_ROOT}/${APP_NAME}/templatetags/majestian_economy_tags.py" <<'PY'
from decimal import Decimal

from django import template

from majestian_economy.models import MajesticCoinSettings
from majestian_economy.services import EconomyEngine


register = template.Library()


@register.filter
def majestic_coins(value):
    try:
        amount = Decimal(str(value))
    except Exception:
        amount = Decimal("0")

    settings_obj = MajesticCoinSettings.load()
    return f"{amount:,.2f} {settings_obj.coin_symbol}"


@register.filter
def majestic_coin_value(value):
    try:
        amount = EconomyEngine.value_from_coins(value)
    except Exception:
        amount = Decimal("0.00")

    return f"${amount:,.2f}"


@register.simple_tag
def majestic_coin_symbol():
    return MajesticCoinSettings.load().coin_symbol
PY

###############################################################################
# 14. TESTS
###############################################################################

cat > "${PROJECT_ROOT}/${APP_NAME}/tests.py" <<'PY'
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import (
    CitizenLevelReward,
    CoinTransaction,
    MajesticCoinSettings,
    MajestianWallet,
)
from .services import EconomyEngine


class MajestianEconomyTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="majestian_test",
            email="majestian@example.com",
            password="NotARealProductionPassword123!",
        )

        self.settings_obj = MajesticCoinSettings.load()
        self.settings_obj.coin_value = Decimal("0.1000")
        self.settings_obj.save()

        self.level, _created = CitizenLevelReward.objects.get_or_create(
            slug="vision",
            defaults={
                "name": "Vision",
                "referral_percentage": Decimal("10.000"),
                "display_order": 10,
            },
        )

    def test_wallet_created_automatically(self):
        self.assertTrue(
            MajestianWallet.objects.filter(user=self.user).exists()
        )

    def test_ten_percent_of_99_equals_99_mc(self):
        calculation = EconomyEngine.calculate_referral(
            Decimal("99.00"),
            Decimal("10.00"),
        )

        self.assertEqual(
            calculation.reward_value,
            Decimal("9.90"),
        )
        self.assertEqual(
            calculation.coins_awarded,
            Decimal("99.00"),
        )

    def test_posted_credit_updates_wallet(self):
        EconomyEngine.create_credit(
            user=self.user,
            coin_amount=Decimal("99.00"),
            transaction_type=(
                CoinTransaction.TransactionType.CITIZEN_REFERRAL
            ),
            description="Test referral reward",
            idempotency_key="test-referral-001",
        )

        wallet = MajestianWallet.objects.get(user=self.user)

        self.assertEqual(
            wallet.available_coins,
            Decimal("99.00"),
        )
        self.assertEqual(
            wallet.lifetime_earned_coins,
            Decimal("99.00"),
        )

    def test_idempotency_prevents_duplicate_reward(self):
        first = EconomyEngine.create_credit(
            user=self.user,
            coin_amount=Decimal("99.00"),
            transaction_type=(
                CoinTransaction.TransactionType.CITIZEN_REFERRAL
            ),
            description="Test referral reward",
            idempotency_key="test-referral-duplicate",
        )

        second = EconomyEngine.create_credit(
            user=self.user,
            coin_amount=Decimal("99.00"),
            transaction_type=(
                CoinTransaction.TransactionType.CITIZEN_REFERRAL
            ),
            description="Duplicate attempt",
            idempotency_key="test-referral-duplicate",
        )

        self.assertEqual(first.pk, second.pk)

        wallet = MajestianWallet.objects.get(user=self.user)

        self.assertEqual(
            wallet.available_coins,
            Decimal("99.00"),
        )
PY

###############################################################################
# 15. REGISTER APP IN INSTALLED_APPS
###############################################################################

"${PYTHON_BIN}" - "${SETTINGS_FILE}" <<'PY'
import ast
import re
import sys
from pathlib import Path

settings_path = Path(sys.argv[1])
text = settings_path.read_text(encoding="utf-8")

app_entry = "majestian_economy.apps.MajestianEconomyConfig"

if app_entry in text or "'majestian_economy'" in text or '"majestian_economy"' in text:
    print("Majestian Economy is already registered in INSTALLED_APPS.")
    raise SystemExit(0)

pattern = re.compile(
    r"(?P<prefix>INSTALLED_APPS\s*=\s*)"
    r"(?P<value>\[[\s\S]*?\]|\([\s\S]*?\))",
    re.MULTILINE,
)

match = pattern.search(text)

if not match:
    raise SystemExit(
        "Could not locate a literal INSTALLED_APPS list or tuple in settings.py"
    )

value_text = match.group("value")

try:
    ast.literal_eval(value_text)
except Exception:
    # It may contain expressions. We can still safely insert before the final
    # closing bracket because the surrounding assignment was identified.
    pass

closing = value_text[-1]
opening_content = value_text[:-1]

if opening_content.rstrip().endswith(","):
    separator = "\n"
else:
    separator = ",\n"

indent_match = re.search(r"\n([ \t]+)[\"']", value_text)
indent = indent_match.group(1) if indent_match else "    "

new_value = (
    opening_content
    + separator
    + f'{indent}"{app_entry}",\n'
    + closing
)

new_text = text[:match.start("value")] + new_value + text[match.end("value"):]

settings_path.write_text(new_text, encoding="utf-8")
print("Registered Majestian Economy in INSTALLED_APPS.")
PY

###############################################################################
# 16. DJANGO MIGRATIONS
###############################################################################

echo
echo "Creating migrations..."
"${PYTHON_BIN}" manage.py makemigrations "${APP_NAME}"

echo
echo "Applying migrations..."
"${PYTHON_BIN}" manage.py migrate

###############################################################################
# 17. CREATE WALLETS FOR EXISTING MAJESTIANS
###############################################################################

echo
echo "Creating wallets for existing accounts..."

"${PYTHON_BIN}" manage.py shell <<'PY'
from django.contrib.auth import get_user_model
from majestian_economy.models import MajestianWallet

User = get_user_model()

created_count = 0

for user in User.objects.iterator():
    _wallet, created = MajestianWallet.objects.get_or_create(user=user)
    if created:
        created_count += 1

print(f"Created {created_count} new Majestian Wallet(s).")
print(f"Total wallets: {MajestianWallet.objects.count()}")
PY

###############################################################################
# 18. RUN TESTS
###############################################################################

echo
echo "Running Majestian Economy tests..."
"${PYTHON_BIN}" manage.py test "${APP_NAME}" --verbosity 1

###############################################################################
# 19. ECONOMY STATUS
###############################################################################

echo
"${PYTHON_BIN}" manage.py majestian_economy_status

###############################################################################
# 20. FINAL PROJECT CHECKS
###############################################################################

echo
echo "Running Django system checks..."
"${PYTHON_BIN}" manage.py check

echo
echo "Collecting static files..."
"${PYTHON_BIN}" manage.py collectstatic --noinput

###############################################################################
# 21. COMPLETE
###############################################################################

echo
echo "=============================================================="
echo "  MAJESTIAN ECONOMY CORE INSTALLED SUCCESSFULLY"
echo "=============================================================="
echo
echo "Default economic standard:"
echo "  1 MC = \$0.10 of platform value"
echo
echo "Default Citizen Level recommendation rewards:"
echo "  Vision:   10%"
echo "  Pro:      12%"
echo "  Elite:    15%"
echo "  Majestic: 20%"
echo
echo "Example:"
echo "  \$99.00 membership x 10% = \$9.90 reward = 99 MC"
echo
echo "Django Admin section:"
echo "  Majestic Economy"
echo
echo "Backup:"
echo "  ${BACKUP_ROOT}"
echo
echo "Useful commands:"
echo "  ${PYTHON_BIN} manage.py majestian_economy_status"
echo "  ${PYTHON_BIN} manage.py post_eligible_coin_rewards"
echo
echo "HISTORY HAS BEEN MADE, KING LEO."
echo "=============================================================="
