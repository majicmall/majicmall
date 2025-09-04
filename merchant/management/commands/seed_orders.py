from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from decimal import Decimal
import random

from merchant.models import MerchantStore, Product, Order, OrderItem

class Command(BaseCommand):
    help = "Seed sample orders for testing the merchant dashboard."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=5,
            help="Number of orders to create (default=5)",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        user = User.objects.order_by("id").first()
        if not user:
            self.stdout.write(self.style.ERROR("No users found. Create a user first."))
            return

        store = getattr(user, "merchant_store", None)
        if not store:
            self.stdout.write(self.style.ERROR("User has no MerchantStore. Create one first."))
            return

        products = list(store.products.all())
        if not products:
            # seed products if none exist yet
            products = [
                Product.objects.create(store=store, name="Majic Tee", price=Decimal("25.00")),
                Product.objects.create(store=store, name="Spark Hoodie", price=Decimal("59.00")),
                Product.objects.create(store=store, name="Glow Mug", price=Decimal("12.50")),
            ]

        statuses = ["pending", "paid", "shipped", "completed"]
        created = 0

        for _ in range(options["count"]):
            order = Order.objects.create(store=store, status=random.choice(statuses))
            subtotal = Decimal("0.00")

            for p in random.sample(products, k=random.randint(1, min(3, len(products)))):
                qty = random.randint(1, 3)
                unit_price = p.price or Decimal("10.00")
                OrderItem.objects.create(
                    order=order,
                    product=p,
                    name=p.name,
                    quantity=qty,
                    unit_price=unit_price,
                )
                subtotal += unit_price * qty

            order.subtotal = subtotal
            order.total = subtotal
            order.save(update_fields=["subtotal", "total"])
            created += 1

        self.stdout.write(self.style.SUCCESS(f"Seeded {created} order(s)."))
