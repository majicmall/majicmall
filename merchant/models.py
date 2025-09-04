# merchant/models.py
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils.timezone import now


# -----------------------------
# 💼 Merchant Store Model
# -----------------------------
class MerchantStore(models.Model):
    PLAN_CHOICES = [
        ("starter", "Starter"),
        ("pro", "Pro"),
        ("elite", "Elite"),
    ]

    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="merchant_store",
    )
    store_name = models.CharField(max_length=100)
    slogan = models.CharField(max_length=150, blank=True)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=100)
    logo = models.ImageField(upload_to="merchant_logos/", blank=True, null=True)
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default="starter")
    created_at = models.DateTimeField(auto_now_add=True)

    # ✅ Archive fields
    is_archived = models.BooleanField(default=False)
    archived_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.store_name

    # ✅ Archive helpers
    def archive(self):
        self.is_archived = True
        self.archived_at = now()
        self.save(update_fields=["is_archived", "archived_at"])

    def can_restore(self) -> bool:
        """Restorable within 7 days of archived_at."""
        return bool(
            self.is_archived
            and self.archived_at
            and now() <= self.archived_at + timedelta(days=7)
        )

    def restore_deadline(self):
        return self.archived_at + timedelta(days=7) if self.archived_at else None

    def restore(self):
        self.is_archived = False
        self.archived_at = None
        self.save(update_fields=["is_archived", "archived_at"])


# -----------------------------
# 🛍️ Product Model
# -----------------------------
class Product(models.Model):
    store = models.ForeignKey(
        MerchantStore,
        on_delete=models.CASCADE,
        related_name="products",
    )
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="product_images/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "core_product"   # <-- use the old table that already has your rows


    def __str__(self):
        return self.name


# -----------------------------
# 🧾 Order Model
# -----------------------------
class Order(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("shipped", "Shipped"),
        ("completed", "Completed"),
        ("refunded", "Refunded"),
        ("canceled", "Canceled"),
    ]

    store = models.ForeignKey(
        MerchantStore,
        on_delete=models.CASCADE,
        related_name="orders",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    session_key = models.CharField(max_length=40, null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="paid")
    note = models.TextField(blank=True)

    # cached totals (optionally recompute in views or signals)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.pk} — {self.store.store_name}"


# -----------------------------
# 🧾 Order Item Model
# -----------------------------
class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",  # used by templates: order.items.all
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,  # keep item history even if product is removed
    )
    # snapshot fields (so historical records don't change if product changes)
    name = models.CharField(max_length=255, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    @property
    def line_total(self) -> Decimal:
        # quantity (int) * unit_price (Decimal) -> Decimal
        return Decimal(self.quantity) * (self.unit_price or Decimal("0.00"))

    def save(self, *args, **kwargs):
        # Snapshot defaults before saving
        if not self.name and self.product_id:
            self.name = self.product.name
        if self.unit_price is None and self.product_id:
            self.unit_price = self.product.price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} x{self.quantity}"


# --- Payment models -------------------------------------------------------------
class MerchantPaymentMethod(models.Model):
    MODE_CHOICES = [
        ("test", "Test"),
        ("live", "Live"),
    ]
    PROVIDER_CHOICES = [
        ("stripe", "Stripe"),
        ("paypal", "PayPal"),
        ("card", "Credit/Debit (On-site)"),
        # add your own identifiers later, e.g. ("myprocessor", "My Processor")
    ]

    store = models.ForeignKey(
        "merchant.MerchantStore",
        on_delete=models.CASCADE,
        related_name="payment_methods",
    )
    provider = models.CharField(max_length=40, choices=PROVIDER_CHOICES)
    display_name = models.CharField(max_length=80, blank=True)
    mode = models.CharField(max_length=10, choices=MODE_CHOICES, default="test")
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)

    # Keep credentials in JSON (API keys, secrets, etc.). NEVER expose in templates.
    credentials = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_default", "provider", "-updated_at"]

    def __str__(self):
        name = self.display_name or self.get_provider_display()
        return f"{name} ({self.mode})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Ensure only one default per store
        if self.is_default:
            MerchantPaymentMethod.objects.filter(store=self.store).exclude(pk=self.pk).update(is_default=False)
