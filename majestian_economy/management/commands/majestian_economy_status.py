from django.core.management.base import BaseCommand
from django.db.models import Sum

from majestian_economy.models import (
    CitizenLevelReward,
    CoinTransaction,
    MajesticCoinSettings,
    MajestianWallet,
)


class Command(BaseCommand):
    help = "Display the current Majestian Economy configuration and totals."

    def handle(self, *args, **options):
        settings_obj = MajesticCoinSettings.load()

        wallets = MajestianWallet.objects.count()

        available = (
            MajestianWallet.objects.aggregate(total=Sum("available_coins"))[
                "total"
            ]
            or 0
        )

        pending = (
            MajestianWallet.objects.aggregate(total=Sum("pending_coins"))[
                "total"
            ]
            or 0
        )

        posted_transactions = CoinTransaction.objects.filter(
            status=CoinTransaction.Status.POSTED
        ).count()

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS("MAJESTIAN ECONOMY STATUS")
        )
        self.stdout.write("=" * 55)
        self.stdout.write(
            f"Coin standard: 1 {settings_obj.coin_symbol} "
            f"= ${settings_obj.coin_value}"
        )
        self.stdout.write(f"Currency:      {settings_obj.currency_code}")
        self.stdout.write(f"Wallets:       {wallets}")
        self.stdout.write(f"Available MC:  {available}")
        self.stdout.write(f"Pending MC:    {pending}")
        self.stdout.write(f"Posted ledger: {posted_transactions}")
        self.stdout.write("")
        self.stdout.write("Citizen Levels:")

        for level in CitizenLevelReward.objects.order_by(
            "display_order",
            "name",
        ):
            active = "Active" if level.is_active else "Inactive"
            self.stdout.write(
                f"  - {level.name}: "
                f"{level.referral_percentage}% ({active})"
            )

        self.stdout.write("")
