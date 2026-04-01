from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils.timezone import now
from django.utils.text import slugify


class MallZone(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            base = slugify(self.name) or "zone"
            candidate = base
            n = 1
            while MallZone.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                n += 1
                candidate = f"{base}-{n}"
            self.slug = candidate
        super().save(*args, **kwargs)


class MerchantStore(models.Model):
    PLAN_CHOICES = [
        ("starter", "Starter"),
        ("pro", "Pro"),
        ("elite", "Elite"),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="stores",
    )
    zone = models.ForeignKey(
        "merchant.MallZone",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stores",
    )
    store_name = models.CharField(max_length=255)
    slogan = models.CharField(max_length=150, blank=True)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=100)
    logo = models.ImageField(upload_to="merchant_logos/", blank=True, null=True)
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default="starter")
    created_at = models.DateTimeField(auto_now_add=True)

    slug = models.SlugField(max_length=255, unique=True, blank=True)
    is_public = models.BooleanField(
        default=getattr(settings, "AUTO_PUBLIC_STOREFRONTS", False)
    )

    is_archived = models.BooleanField(default=False)
    archived_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.store_name

    def save(self, *args, **kwargs):
        if not self.slug and self.store_name:
            base = slugify(self.store_name) or "store"
            candidate = base
            n = 1
            while MerchantStore.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                n += 1
                candidate = f"{base}-{n}"
            self.slug = candidate
        super().save(*args, **kwargs)

    def archive(self):
        self.is_archived = True
        self.archived_at = now()
        self.save(update_fields=["is_archived", "archived_at"])

    def can_restore(self) -> bool:
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


class StoreCategory(models.Model):
    store = models.ForeignKey(
        MerchantStore,
        on_delete=models.CASCADE,
        related_name="categories",
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, blank=True)

    class Meta:
        unique_together = ("store", "slug")
        ordering = ["name"]

    def __str__(self):
        return f"{self.store.store_name} - {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            base = slugify(self.name) or "category"
            candidate = base
            n = 1
            while StoreCategory.objects.filter(store=self.store, slug=candidate).exclude(pk=self.pk).exists():
                n += 1
                candidate = f"{base}-{n}"
            self.slug = candidate
        super().save(*args, **kwargs)


class Product(models.Model):
    PRODUCT_TYPE_CHOICES = [
        ("physical", "Physical"),
        ("digital", "Digital"),
    ]

    store = models.ForeignKey(
        MerchantStore,
        on_delete=models.CASCADE,
        related_name="products",
    )
    category = models.ForeignKey(
        "merchant.StoreCategory",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )
    name = models.CharField(max_length=255)
    product_type = models.CharField(
        max_length=10,
        choices=PRODUCT_TYPE_CHOICES,
        default="physical",
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="product_images/", blank=True, null=True)
    digital_file = models.FileField(upload_to="digital_products/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "core_product"

    def __str__(self):
        return self.name

    @property
    def is_digital(self) -> bool:
        return self.product_type == "digital"

    @property
    def is_physical(self) -> bool:
        return self.product_type == "physical"


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

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.pk} — {self.store.store_name}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
    )
    name = models.CharField(max_length=255, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    @property
    def line_total(self) -> Decimal:
        return Decimal(self.quantity) * (self.unit_price or Decimal("0.00"))

    def save(self, *args, **kwargs):
        if not self.name and self.product_id:
            self.name = self.product.name
        if self.unit_price is None and self.product_id:
            self.unit_price = self.product.price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} x{self.quantity}"


class MerchantPaymentMethod(models.Model):
    MODE_CHOICES = [
        ("test", "Test"),
        ("live", "Live"),
    ]
    PROVIDER_CHOICES = [
        ("stripe", "Stripe"),
        ("paypal", "PayPal"),
        ("card", "Credit/Debit (On-site)"),
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
        if self.is_default:
            MerchantPaymentMethod.objects.filter(store=self.store).exclude(pk=self.pk).update(is_default=False)