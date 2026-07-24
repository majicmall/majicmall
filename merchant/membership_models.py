"""
MajicMall Megaverse merchant membership database models.

These models are imported by merchant/models.py so Django discovers
them as part of the merchant application.
"""

from django.conf import settings
from django.db import models


class MerchantMembership(models.Model):
    STATUS_PENDING = "pending"
    STATUS_ACTIVE = "active"
    STATUS_FOUNDATION = "foundation"
    STATUS_GRACE = "grace"
    STATUS_SUSPENDED = "suspended"
    STATUS_CANCELLED = "cancelled"
    STATUS_EXPIRED = "expired"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_FOUNDATION, "Foundation"),
        (STATUS_GRACE, "Grace Period"),
        (STATUS_SUSPENDED, "Suspended"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_EXPIRED, "Expired"),
    ]

    PLAN_VISION = "vision"
    PLAN_PRO = "pro"
    PLAN_ELITE = "elite"
    PLAN_ENTERPRISE = "enterprise"
    PLAN_MAJESTIC = "majestic"
    PLAN_FOUNDATION = "foundation"

    PLAN_CHOICES = [
        (PLAN_VISION, "Vision"),
        (PLAN_PRO, "Pro"),
        (PLAN_ELITE, "Elite"),
        (PLAN_ENTERPRISE, "Enterprise"),
        (PLAN_MAJESTIC, "Majestic"),
        (PLAN_FOUNDATION, "Foundation Merchant"),
    ]

    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="merchant_membership",
    )

    primary_store = models.ForeignKey(
        "merchant.MerchantStore",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="membership_records",
    )

    current_plan = models.CharField(
        max_length=20,
        choices=PLAN_CHOICES,
        default=PLAN_VISION,
    )

    previous_plan = models.CharField(
        max_length=20,
        choices=PLAN_CHOICES,
        blank=True,
        default="",
    )

    transition_plan = models.CharField(
        max_length=20,
        choices=PLAN_CHOICES,
        blank=True,
        default="",
        help_text=(
            "Plan scheduled to begin after a complimentary or "
            "promotional membership ends."
        ),
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
    )

    member_since = models.DateTimeField()

    anniversary_date = models.DateField()

    next_billing_date = models.DateField(
        null=True,
        blank=True,
    )

    renewal_date = models.DateField(
        null=True,
        blank=True,
    )

    complimentary_until = models.DateField(
        null=True,
        blank=True,
    )

    foundation_expires_on = models.DateField(
        null=True,
        blank=True,
    )

    last_plan_change_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    is_foundation_member = models.BooleanField(default=False)

    foundation_pass_verified = models.BooleanField(default=False)

    foundation_member_number = models.CharField(
        max_length=30,
        unique=True,
        null=True,
        blank=True,
    )

    majestic_coins_awarded = models.BooleanField(default=False)

    majestic_coins_awarded_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-member_since"]
        verbose_name = "Merchant Membership"
        verbose_name_plural = "Merchant Memberships"

    def __str__(self):
        return (
            f"{self.owner} — "
            f"{self.get_current_plan_display()} Membership"
        )


class MerchantMembershipHistory(models.Model):
    CHANGE_CREATED = "created"
    CHANGE_UPGRADE = "upgrade"
    CHANGE_DOWNGRADE = "downgrade"
    CHANGE_RENEWAL = "renewal"
    CHANGE_EXTENSION = "extension"
    CHANGE_STATUS = "status"
    CHANGE_PAYMENT = "payment"
    CHANGE_ADMIN = "admin"

    CHANGE_TYPE_CHOICES = [
        (CHANGE_CREATED, "Membership Created"),
        (CHANGE_UPGRADE, "Plan Upgrade"),
        (CHANGE_DOWNGRADE, "Plan Downgrade"),
        (CHANGE_RENEWAL, "Membership Renewal"),
        (CHANGE_EXTENSION, "Complimentary Extension"),
        (CHANGE_STATUS, "Status Change"),
        (CHANGE_PAYMENT, "Payment Change"),
        (CHANGE_ADMIN, "Administrative Change"),
    ]

    membership = models.ForeignKey(
        MerchantMembership,
        on_delete=models.CASCADE,
        related_name="history",
    )

    change_type = models.CharField(
        max_length=20,
        choices=CHANGE_TYPE_CHOICES,
        default=CHANGE_CREATED,
    )

    previous_plan = models.CharField(
        max_length=20,
        blank=True,
        default="",
    )

    new_plan = models.CharField(
        max_length=20,
        blank=True,
        default="",
    )

    previous_status = models.CharField(
        max_length=20,
        blank=True,
        default="",
    )

    new_status = models.CharField(
        max_length=20,
        blank=True,
        default="",
    )

    effective_date = models.DateTimeField()

    note = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-effective_date", "-id"]
        verbose_name = "Membership History"
        verbose_name_plural = "Membership Histories"

    def __str__(self):
        return (
            f"{self.membership.owner} — "
            f"{self.get_change_type_display()}"
        )


class MajesticCoinWallet(models.Model):
    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="majestic_coin_wallet",
    )

    balance = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.owner} — {self.balance} Majestic Coins"


class MajesticCoinTransaction(models.Model):
    TYPE_AWARD = "award"
    TYPE_CREDIT = "credit"
    TYPE_DEBIT = "debit"
    TYPE_PURCHASE = "purchase"
    TYPE_ADJUSTMENT = "adjustment"

    TRANSACTION_TYPES = [
        (TYPE_AWARD, "Award"),
        (TYPE_CREDIT, "Credit"),
        (TYPE_DEBIT, "Debit"),
        (TYPE_PURCHASE, "Purchase"),
        (TYPE_ADJUSTMENT, "Adjustment"),
    ]

    wallet = models.ForeignKey(
        MajesticCoinWallet,
        on_delete=models.CASCADE,
        related_name="transactions",
    )

    amount = models.IntegerField()

    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPES,
        default=TYPE_AWARD,
    )

    reason = models.CharField(max_length=255)

    reference = models.CharField(
        max_length=150,
        unique=True,
        help_text="Unique reference that prevents duplicate transactions.",
    )

    balance_after = models.IntegerField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        sign = "+" if self.amount >= 0 else ""
        return f"{sign}{self.amount} — {self.reason}"
