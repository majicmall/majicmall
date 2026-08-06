from django.core.management.base import BaseCommand

from advertising.services import sync_campaign_states


class Command(BaseCommand):
    help = (
        "Advance scheduled advertising campaigns, activate live "
        "campaigns, complete expired campaigns, and refresh inventory."
    )

    def handle(self, *args, **options):
        result = sync_campaign_states()

        self.stdout.write(
            self.style.SUCCESS(
                "Advertising campaign synchronization complete."
            )
        )

        self.stdout.write(
            f"Scheduled: {result.scheduled}"
        )

        self.stdout.write(
            f"Activated: {result.activated}"
        )

        self.stdout.write(
            f"Completed: {result.completed}"
        )

        self.stdout.write(
            "Inventory records updated: "
            f"{result.inventory_updated}"
        )
