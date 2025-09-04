from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils.text import slugify

from core.models import Merchant
from merchant.models import MerchantStore


def ensure_unique_slug(base: str) -> str:
    """
    Return a slug derived from `base`, appending -<n> until it's unique.
    """
    base = slugify(base) or "merchant"
    slug = base
    i = 1
    while Merchant.objects.filter(slug=slug).exists():
        i += 1
        slug = f"{base}-{i}"
    return slug


class Command(BaseCommand):
    help = "Create missing Merchant and MerchantStore rows for existing users."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be created/updated without writing to the DB.",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        dry_run = options["dry_run"]

        users = User.objects.all().order_by("id")
        created_merchants = 0
        updated_merchants = 0
        created_stores = 0

        for u in users:
            # --- Ensure Merchant ---
            merchant = getattr(u, "merchant", None)
            if merchant is None:
                display_name = u.username or f"merchant-{u.pk}"
                slug = ensure_unique_slug(display_name)
                if dry_run:
                    self.stdout.write(f"[DRY-RUN] Create Merchant for user={u.id} '{display_name}' slug='{slug}'")
                else:
                    Merchant.objects.create(
                        user=u,
                        display_name=display_name,
                        slug=slug,
                        email=getattr(u, "email", "") or "",
                        plan="starter",
                    )
                created_merchants += 1
                # refresh relation for store logic below (only if not dry-run)
                merchant = None
            else:
                changed = False
                if not merchant.display_name:
                    merchant.display_name = u.username or f"merchant-{merchant.pk}"
                    changed = True
                if not merchant.slug:
                    merchant.slug = ensure_unique_slug(merchant.display_name)
                    changed = True

                if changed:
                    if dry_run:
                        self.stdout.write(f"[DRY-RUN] Update Merchant {merchant.pk} for user={u.id}")
                    else:
                        merchant.save(update_fields=["display_name", "slug"])
                    updated_merchants += 1

            # --- Ensure at least one MerchantStore for this user ---
            has_store = MerchantStore.objects.filter(owner=u).exists()
            if not has_store:
                store_name = f"{u.username}'s Store" if u.username else "My Store"
                if dry_run:
                    self.stdout.write(f"[DRY-RUN] Create MerchantStore for user={u.id} '{store_name}'")
                else:
                    MerchantStore.objects.create(
                        owner=u,
                        store_name=store_name,
                        slogan="Welcome to my store!",
                        category="General",
                        plan="starter",
                        description="Auto-created store inside Majic Mall.",
                    )
                created_stores += 1

        summary = (
            f"Done. Merchants: +{created_merchants} created, {updated_merchants} updated. "
            f"Stores: +{created_stores} created."
        )
        if dry_run:
            summary = "[DRY-RUN] " + summary
        self.stdout.write(self.style.SUCCESS(summary))

