from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import (
    CitizenLevelReward,
    CoinTransaction,
    MajesticCoinSettings,
    MajestianWallet,
)
from .services import EconomyEngine


class MajestianEconomyTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="majestian_test",
            email="majestian@example.com",
            password="NotARealProductionPassword123!",
        )

        self.settings_obj = MajesticCoinSettings.load()
        self.settings_obj.coin_value = Decimal("0.1000")
        self.settings_obj.save()

        self.level, _created = CitizenLevelReward.objects.get_or_create(
            slug="vision",
            defaults={
                "name": "Vision",
                "referral_percentage": Decimal("10.000"),
                "display_order": 10,
            },
        )

    def test_wallet_created_automatically(self):
        self.assertTrue(
            MajestianWallet.objects.filter(user=self.user).exists()
        )

    def test_ten_percent_of_99_equals_99_mc(self):
        calculation = EconomyEngine.calculate_referral(
            Decimal("99.00"),
            Decimal("10.00"),
        )

        self.assertEqual(
            calculation.reward_value,
            Decimal("9.90"),
        )
        self.assertEqual(
            calculation.coins_awarded,
            Decimal("99.00"),
        )

    def test_posted_credit_updates_wallet(self):
        EconomyEngine.create_credit(
            user=self.user,
            coin_amount=Decimal("99.00"),
            transaction_type=(
                CoinTransaction.TransactionType.CITIZEN_REFERRAL
            ),
            description="Test referral reward",
            idempotency_key="test-referral-001",
        )

        wallet = MajestianWallet.objects.get(user=self.user)

        self.assertEqual(
            wallet.available_coins,
            Decimal("99.00"),
        )
        self.assertEqual(
            wallet.lifetime_earned_coins,
            Decimal("99.00"),
        )

    def test_idempotency_prevents_duplicate_reward(self):
        first = EconomyEngine.create_credit(
            user=self.user,
            coin_amount=Decimal("99.00"),
            transaction_type=(
                CoinTransaction.TransactionType.CITIZEN_REFERRAL
            ),
            description="Test referral reward",
            idempotency_key="test-referral-duplicate",
        )

        second = EconomyEngine.create_credit(
            user=self.user,
            coin_amount=Decimal("99.00"),
            transaction_type=(
                CoinTransaction.TransactionType.CITIZEN_REFERRAL
            ),
            description="Duplicate attempt",
            idempotency_key="test-referral-duplicate",
        )

        self.assertEqual(first.pk, second.pk)

        wallet = MajestianWallet.objects.get(user=self.user)

        self.assertEqual(
            wallet.available_coins,
            Decimal("99.00"),
        )
