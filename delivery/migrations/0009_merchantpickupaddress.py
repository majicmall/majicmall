from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("delivery", "0008_deliverypartner_documents_reviewed_by_and_more"),
        ("merchant", "0019_order_alert_acknowledged_at_order_estimated_ready_at_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="MerchantPickupAddress",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "address_line_1",
                    models.CharField(
                        max_length=255,
                        verbose_name="Street Address",
                    ),
                ),
                (
                    "address_line_2",
                    models.CharField(
                        blank=True,
                        max_length=120,
                        verbose_name=(
                            "Suite, Unit, Floor, or Building"
                        ),
                    ),
                ),
                (
                    "city",
                    models.CharField(max_length=100),
                ),
                (
                    "state",
                    models.CharField(max_length=100),
                ),
                (
                    "postal_code",
                    models.CharField(
                        max_length=20,
                        verbose_name="ZIP / Postal Code",
                    ),
                ),
                (
                    "pickup_instructions",
                    models.TextField(
                        blank=True,
                        help_text=(
                            "Examples: Use the rear entrance, "
                            "ask for the manager, park in pickup "
                            "space number 3, or ring the "
                            "loading-door bell."
                        ),
                    ),
                ),
                (
                    "is_verified",
                    models.BooleanField(default=False),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True),
                ),
                (
                    "store",
                    models.OneToOneField(
                        on_delete=(
                            django.db.models.deletion.CASCADE
                        ),
                        related_name="driver_pickup_address",
                        to="merchant.merchantstore",
                    ),
                ),
            ],
            options={
                "verbose_name": "Merchant Pickup Address",
                "verbose_name_plural": (
                    "Merchant Pickup Addresses"
                ),
            },
        ),
    ]
