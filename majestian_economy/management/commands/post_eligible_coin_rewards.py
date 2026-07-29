from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.utils import timezone

from majestian_economy.models import CoinTransaction
from majestian_economy.services import EconomyEngine


class Command(BaseCommand):
    help = "Post pending Majestic Coin rewards whose holding period has ended."

    def handle(self, *args, **options):
        eligible = CoinTransaction.objects.filter(
            status=CoinTransaction.Status.PENDING,
            direction=CoinTransaction.Direction.CREDIT,
            available_at__lte=timezone.now(),
        ).order_by("available_at", "id")

        posted = 0
        skipped = 0

        for entry in eligible.iterator():
            try:
                EconomyEngine.post_pending_transaction(entry)
                posted += 1
            except ValidationError as exc:
                skipped += 1
                self.stderr.write(
                    f"Skipped {entry.public_id}: {exc}"
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Posted {posted} eligible Majestic Coin reward(s)."
            )
        )

        if skipped:
            self.stdout.write(
                self.style.WARNING(
                    f"Skipped {skipped} reward(s)."
                )
            )
