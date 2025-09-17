from django.db import migrations, models
from django.utils.text import slugify


def backfill_slugs(apps, schema_editor):
    Store = apps.get_model("merchant", "MerchantStore")

    # gather existing non-empty slugs, if any
    used = set(
        s for s in
        Store.objects.exclude(slug__isnull=True).exclude(slug__exact="").values_list("slug", flat=True)
    )

    for store in Store.objects.all().order_by("id"):
        # prefer any existing slug value; else derive from store_name; else fallback
        base = None
        if getattr(store, "slug", None):
            base = slugify(store.slug)
        if not base:
            base = slugify(getattr(store, "store_name", "") or "") or f"store-{store.id}"

        cand = base
        n = 1
        while cand in used:
            n += 1
            cand = f"{base}-{n}"

        if store.slug != cand:
            store.slug = cand
            store.save(update_fields=["slug"])

        used.add(store.slug)


class Migration(migrations.Migration):

    dependencies = [
        ("merchant", "0006_alter_product_table"),
    ]

    operations = [
        # Add fields permissively first (slug nullable so we can backfill)
        migrations.AddField(
            model_name="merchantstore",
            name="is_public",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="merchantstore",
            name="slug",
            field=models.SlugField(max_length=255, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name="merchantstore",
            name="store_name",
            field=models.CharField(max_length=255),
        ),

        # Backfill unique slugs for existing rows
        migrations.RunPython(backfill_slugs, reverse_code=migrations.RunPython.noop),

        # Enforce uniqueness only after backfill
        migrations.AlterField(
            model_name="merchantstore",
            name="slug",
            field=models.SlugField(max_length=255, unique=True),
        ),
    ]
