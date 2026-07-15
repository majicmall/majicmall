from django.core.management.base import BaseCommand

from delivery.dispatch_engine import (
    order_is_dispatch_ready,
    transport_partner_coverage,
)
from delivery.models import DeliveryJob


class Command(BaseCommand):
    help = (
        "Show which MajicMall Megaverse delivery jobs are ready "
        "for Transport Partner dispatch."
    )

    def handle(self, *args, **options):
        jobs = (
            DeliveryJob.objects
            .filter(
                status="pending",
                partner__isnull=True,
            )
            .select_related(
                "store",
                "order",
            )
            .order_by("id")
        )

        if not jobs.exists():
            self.stdout.write(
                self.style.WARNING(
                    "No pending unassigned delivery jobs found."
                )
            )
            return

        for job in jobs:
            ready = order_is_dispatch_ready(job.order)
            coverage = transport_partner_coverage(
                job.delivery_zip
            )

            self.stdout.write("")
            self.stdout.write(
                f"Delivery Job #{job.id}"
            )
            self.stdout.write(
                f"Order: #{job.order_id}"
            )
            self.stdout.write(
                f"Store: {job.store.store_name}"
            )
            self.stdout.write(
                "Fulfillment status: "
                f"{job.order.fulfillment_status}"
            )
            self.stdout.write(
                "Merchant released: "
                f"{'YES' if ready else 'NO'}"
            )
            self.stdout.write(
                "Available Transport Partners: "
                f"{coverage['available_count']}"
            )
            self.stdout.write(
                "Visible to partners: "
                f"{'YES' if ready and coverage['available'] else 'NO'}"
            )
