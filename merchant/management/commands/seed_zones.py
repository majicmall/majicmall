from django.core.management.base import BaseCommand
from merchant.models import MallZone


class Command(BaseCommand):
    help = "Seed default mall zones"

    def handle(self, *args, **options):
        zones = [
            "Fashion Zone",
            "Tech Zone",
            "Food Court",
            "Theater Zone",
            "Music Zone",
            "Business Services Zone",
            "ATL's Hottest Zone",
        ]

        created = 0
        for name in zones:
            obj, was_created = MallZone.objects.get_or_create(name=name)
            if was_created:
                created += 1
                self.stdout.write(self.style.SUCCESS(f"Created: {name}"))
            else:
                self.stdout.write(f"Exists: {name}")

        self.stdout.write(self.style.SUCCESS(f"\nDone. {created} new zones added."))