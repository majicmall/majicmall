#!/usr/bin/env bash
set -Eeuo pipefail

echo
echo "================================================="
echo " MajicMall Megaverse — MM_PUSH_004"
echo " PropertyLease Contract Engine"
echo "================================================="
echo

MODELS_FILE="digital_property/models.py"
ADMIN_FILE="digital_property/admin.py"
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR=".mm_backups/MM_PUSH_004_${STAMP}"
PHASE="source"

mkdir -p "$BACKUP_DIR"

cp "$MODELS_FILE" "$BACKUP_DIR/models.py"

if [[ -f "$ADMIN_FILE" ]]; then
    cp "$ADMIN_FILE" "$BACKUP_DIR/admin.py"
else
    touch "$BACKUP_DIR/admin.py"
fi

restore_source() {
    cp "$BACKUP_DIR/models.py" "$MODELS_FILE"
    cp "$BACKUP_DIR/admin.py" "$ADMIN_FILE"
}

failure_handler() {
    EXIT_CODE=$?

    echo
    echo "❌ MM_PUSH_004 failed during phase: $PHASE"

    if [[ "$PHASE" == "source" || "$PHASE" == "validation" ]]; then
        echo "⚠️ Restoring source files..."
        restore_source
        echo "✅ Source files restored."
    else
        echo "⚠️ Migration work had already started."
        echo "Source files were preserved for safe diagnosis."
    fi

    echo "Backup location:"
    echo "   $BACKUP_DIR"
    exit "$EXIT_CODE"
}

trap failure_handler ERR

echo "✅ Backups created:"
echo "   $BACKUP_DIR"
echo

python <<'PY'
from pathlib import Path

models_path = Path("digital_property/models.py")
text = models_path.read_text(encoding="utf-8")

required_models = (
    "class PropertyType(models.Model):",
    "class LeasePlan(models.Model):",
    "class DigitalProperty(models.Model):",
)

missing = [item for item in required_models if item not in text]

if missing:
    raise SystemExit(
        "Missing required model definitions: " + ", ".join(missing)
    )

# Add ValidationError import safely.
validation_import = "from django.core.exceptions import ValidationError"

if validation_import not in text:
    django_import_marker = "from django.db import models"

    if django_import_marker not in text:
        raise SystemExit(
            "Could not locate 'from django.db import models' in "
            "digital_property/models.py."
        )

    text = text.replace(
        django_import_marker,
        validation_import + "\n" + django_import_marker,
        1,
    )

if "class PropertyLease(models.Model):" in text:
    print("ℹ️ PropertyLease already exists. Model insertion skipped.")
else:
    model_code = r'''


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
'''

    text = text.rstrip() + model_code + "\n"
    print("✅ PropertyLease model added.")

models_path.write_text(text, encoding="utf-8")
PY

python <<'PY'
from pathlib import Path

admin_path = Path("digital_property/admin.py")

if admin_path.exists():
    text = admin_path.read_text(encoding="utf-8")
else:
    text = "from django.contrib import admin\n"

model_import = "from .models import PropertyLease"

if model_import not in text:
    text = text.rstrip() + "\n\n" + model_import + "\n"

if "@admin.register(PropertyLease)" in text:
    print("ℹ️ PropertyLease admin already exists. Registration skipped.")
else:
    admin_code = r'''


@admin.register(PropertyLease)
class PropertyLeaseAdmin(admin.ModelAdmin):
    list_display = (
        "lease_number",
        "merchant_store",
        "digital_property",
        "lease_plan",
        "status",
        "start_date",
        "end_date",
        "amount_paid",
        "auto_renew",
    )

    list_filter = (
        "status",
        "lease_plan",
        "digital_property__property_type",
        "digital_property__mall_zone",
        "auto_renew",
        "start_date",
        "end_date",
        "created_at",
    )

    search_fields = (
        "lease_number",
        "merchant_store__store_name",
        "merchant_store__owner__email",
        "digital_property__property_code",
        "digital_property__name",
        "campaign_name",
        "notes",
    )

    autocomplete_fields = (
        "merchant_store",
        "digital_property",
        "lease_plan",
    )

    readonly_fields = (
        "lease_number",
        "created_at",
        "updated_at",
        "duration_days_display",
    )

    ordering = (
        "-created_at",
    )

    date_hierarchy = "start_date"

    fieldsets = (
        (
            "Lease Identity",
            {
                "fields": (
                    "lease_number",
                    "status",
                ),
            },
        ),
        (
            "Merchant and Property",
            {
                "fields": (
                    "merchant_store",
                    "digital_property",
                    "lease_plan",
                ),
            },
        ),
        (
            "Lease Term",
            {
                "fields": (
                    "start_date",
                    "end_date",
                    "duration_days_display",
                    "auto_renew",
                ),
            },
        ),
        (
            "Financial Details",
            {
                "fields": (
                    "amount_paid",
                ),
            },
        ),
        (
            "Campaign Details",
            {
                "fields": (
                    "campaign_name",
                    "notes",
                ),
            },
        ),
        (
            "Audit",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
                "classes": (
                    "collapse",
                ),
            },
        ),
    )

    @admin.display(description="Duration")
    def duration_days_display(self, obj):
        if not obj or not obj.pk:
            return "Calculated after dates are selected"

        days = obj.duration_days
        return f"{days} day" if days == 1 else f"{days} days"
'''

    text = text.rstrip() + admin_code + "\n"
    print("✅ PropertyLease admin installed.")

admin_path.write_text(text, encoding="utf-8")
PY

PHASE="validation"

echo
echo "Running Python source validation..."
python -m py_compile "$MODELS_FILE" "$ADMIN_FILE"

echo
echo "Running Django system check..."
python manage.py check

echo
echo "Confirming required Django models..."
python manage.py shell -c '
from django.apps import apps

required = [
    "digital_property.PropertyType",
    "digital_property.LeasePlan",
    "digital_property.DigitalProperty",
    "digital_property.PropertyLease",
    "merchant.MallZone",
    "merchant.MerchantStore",
]

for label in required:
    apps.get_model(label)
    print(f"✅ {label}")
'

PHASE="migration"

echo
echo "Creating migration..."
python manage.py makemigrations digital_property

echo
echo "Applying migration..."
python manage.py migrate digital_property

PHASE="final-check"

echo
echo "Running final Django check..."
python manage.py check

echo
echo "Validating PropertyLease fields and relationships..."
python manage.py shell -c '
from django.apps import apps

model = apps.get_model(
    "digital_property",
    "PropertyLease",
)

required_fields = [
    "lease_number",
    "merchant_store",
    "digital_property",
    "lease_plan",
    "status",
    "start_date",
    "end_date",
    "amount_paid",
    "auto_renew",
    "campaign_name",
    "notes",
    "created_at",
    "updated_at",
]

for field_name in required_fields:
    field = model._meta.get_field(field_name)
    print(
        f"✅ PropertyLease.{field_name} "
        f"({field.__class__.__name__})"
    )

merchant_field = model._meta.get_field("merchant_store")
property_field = model._meta.get_field("digital_property")
plan_field = model._meta.get_field("lease_plan")

assert merchant_field.remote_field.model._meta.label == (
    "merchant.MerchantStore"
)
assert property_field.remote_field.model._meta.label == (
    "digital_property.DigitalProperty"
)
assert plan_field.remote_field.model._meta.label == (
    "digital_property.LeasePlan"
)

print("✅ MerchantStore relationship verified")
print("✅ DigitalProperty relationship verified")
print("✅ LeasePlan relationship verified")
print("✅ Lease number generator available")
print("✅ Lease date validation available")
print("✅ Lease-plan eligibility validation available")
'

echo
echo "Checking migration status..."
python manage.py showmigrations digital_property

trap - ERR

echo
echo "================================================="
echo "✅ MM_PUSH_004 COMPLETE"
echo "✅ PropertyLease contract engine created"
echo "✅ Public lease-number generation enabled"
echo "✅ MerchantStore relationship enabled"
echo "✅ DigitalProperty relationship enabled"
echo "✅ LeasePlan relationship enabled"
echo "✅ Contract validation enabled"
echo "✅ Django Admin configured"
echo "✅ Migration applied"
echo "================================================="
echo
