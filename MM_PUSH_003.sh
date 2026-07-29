#!/usr/bin/env bash
set -Eeuo pipefail

echo
echo "================================================="
echo " MajicMall Megaverse — MM_PUSH_003"
echo " DigitalProperty Inventory Engine"
echo "================================================="
echo

MODELS_FILE="digital_property/models.py"
ADMIN_FILE="digital_property/admin.py"
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR=".mm_backups/MM_PUSH_003_${STAMP}"
PHASE="source"

mkdir -p "$BACKUP_DIR"
cp "$MODELS_FILE" "$BACKUP_DIR/models.py"
cp "$ADMIN_FILE" "$BACKUP_DIR/admin.py"

restore_source() {
    cp "$BACKUP_DIR/models.py" "$MODELS_FILE"
    cp "$BACKUP_DIR/admin.py" "$ADMIN_FILE"
}

failure_handler() {
    EXIT_CODE=$?

    echo
    echo "❌ MM_PUSH_003 failed during phase: $PHASE"

    if [[ "$PHASE" == "source" || "$PHASE" == "validation" ]]; then
        echo "⚠️ Restoring source files..."
        restore_source
        echo "✅ Source files restored."
    else
        echo "⚠️ Migration work had already started."
        echo "Source files were preserved for safe diagnosis."
    fi

    echo "Backup location: $BACKUP_DIR"
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
)

missing = [item for item in required_models if item not in text]
if missing:
    raise SystemExit(
        "Missing required model definitions: " + ", ".join(missing)
    )

if "class DigitalProperty(models.Model):" in text:
    print("ℹ️ DigitalProperty already exists. Model insertion skipped.")
else:
    model_code = r'''

class DigitalProperty(models.Model):
    """
    A leasable digital advertising or promotional location inside
    MajicMall Megaverse.
    """

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

    def __str__(self):
        return f"{self.property_code} — {self.name}"
'''

    models_path.write_text(
        text.rstrip() + model_code + "\n",
        encoding="utf-8",
    )
    print("✅ DigitalProperty model added.")
PY

python <<'PY'
from pathlib import Path

admin_path = Path("digital_property/admin.py")

if admin_path.exists():
    text = admin_path.read_text(encoding="utf-8")
else:
    text = "from django.contrib import admin\n"

if "from .models import DigitalProperty" not in text:
    text = text.rstrip() + "\n\nfrom .models import DigitalProperty\n"

if "@admin.register(DigitalProperty)" not in text:
    text += r'''


@admin.register(DigitalProperty)
class DigitalPropertyAdmin(admin.ModelAdmin):
    list_display = (
        "property_code",
        "name",
        "property_type",
        "mall_zone",
        "availability_status",
        "featured",
        "active",
    )

    list_filter = (
        "property_type",
        "mall_zone",
        "availability_status",
        "supports_image",
        "supports_video",
        "interactive",
        "featured",
        "active",
    )

    search_fields = (
        "property_code",
        "name",
        "slug",
        "description",
        "location_label",
    )

    filter_horizontal = ("lease_plans",)

    prepopulated_fields = {
        "slug": ("name",),
    }

    ordering = (
        "display_order",
        "name",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )
'''

admin_path.write_text(text, encoding="utf-8")
print("✅ DigitalProperty admin installed.")
PY

PHASE="validation"

echo
echo "Running source validation..."
python -m py_compile "$MODELS_FILE" "$ADMIN_FILE"
python manage.py check

echo
echo "Confirming required Django models..."
python manage.py shell -c '
from django.apps import apps

required = [
    "digital_property.PropertyType",
    "digital_property.LeasePlan",
    "digital_property.DigitalProperty",
    "merchant.MallZone",
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
echo "Validating DigitalProperty fields..."
python manage.py shell -c '
from django.apps import apps

model = apps.get_model("digital_property", "DigitalProperty")

required_fields = [
    "property_code",
    "name",
    "slug",
    "property_type",
    "mall_zone",
    "lease_plans",
    "description",
    "location_label",
    "width",
    "height",
    "supports_image",
    "supports_video",
    "interactive",
    "availability_status",
    "featured",
    "active",
    "display_order",
    "created_at",
    "updated_at",
]

for field_name in required_fields:
    model._meta.get_field(field_name)
    print(f"✅ DigitalProperty.{field_name}")
'

trap - ERR

echo
echo "================================================="
echo "✅ MM_PUSH_003 COMPLETE"
echo "✅ DigitalProperty created"
echo "✅ Multiple LeasePlans enabled"
echo "✅ MallZone connection enabled"
echo "✅ Django Admin configured"
echo "✅ Migration applied"
echo "================================================="
echo
