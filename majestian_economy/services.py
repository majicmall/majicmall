from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from .models import (
    CitizenLevelReward,
    CoinTransaction,
    MajesticCoinSettings,
    MajestianRecommendation,
    MajestianWallet,
)


COIN_QUANTIZER = Decimal("0.01")
MONEY_QUANTIZER = Decimal("0.01")
PERCENT_DIVISOR = Decimal("100")


@dataclass(frozen=True)
class ReferralCalculation:
    membership_amount: Decimal
    referral_percentage: Decimal
    reward_value: Decimal
    coin_value: Decimal
    coins_awarded: Decimal


class EconomyEngine:
    """
    Central service for all Majestic Coin calculations and ledger activity.

    Views, checkout systems, admin actions, subscriptions, creator tools,
    advertising systems, and future AI executives should call this service
    instead of updating wallet balances directly.
    """

    @staticmethod
    def decimal(value: Any) -> Decimal:
        try:
            return Decimal(str(value))
        except Exception as exc:
            raise ValidationError(f"Invalid decimal value: {value}") from exc

    @classmethod
    def economy_settings(cls) -> MajesticCoinSettings:
        return MajesticCoinSettings.load()

    @classmethod
    def coins_from_value(
        cls,
        platform_value: Decimal | str | int | float,
    ) -> Decimal:
        settings_obj = cls.economy_settings()
        value = cls.decimal(platform_value)

        if value < 0:
            raise ValidationError("Platform value cannot be negative.")

        if settings_obj.coin_value <= 0:
            raise ValidationError("Majestic Coin value must be greater than zero.")

        return (
            value / settings_obj.coin_value
        ).quantize(COIN_QUANTIZER, rounding=ROUND_HALF_UP)

    @classmethod
    def value_from_coins(
        cls,
        coin_amount: Decimal | str | int | float,
    ) -> Decimal:
        settings_obj = cls.economy_settings()
        coins = cls.decimal(coin_amount)

        if coins < 0:
            raise ValidationError("Coin amount cannot be negative.")

        return (
            coins * settings_obj.coin_value
        ).quantize(MONEY_QUANTIZER, rounding=ROUND_HALF_UP)

    @classmethod
    def calculate_referral(
        cls,
        membership_amount: Decimal | str | int | float,
        referral_percentage: Decimal | str | int | float,
    ) -> ReferralCalculation:
        settings_obj = cls.economy_settings()

        amount = cls.decimal(membership_amount).quantize(
            MONEY_QUANTIZER,
            rounding=ROUND_HALF_UP,
        )
        percentage = cls.decimal(referral_percentage)

        if amount < 0:
            raise ValidationError("Membership amount cannot be negative.")

        if percentage < 0 or percentage > 100:
            raise ValidationError(
                "Referral percentage must be between 0 and 100."
            )

        reward_value = (
            amount * percentage / PERCENT_DIVISOR
        ).quantize(MONEY_QUANTIZER, rounding=ROUND_HALF_UP)

        coins_awarded = (
            reward_value / settings_obj.coin_value
        ).quantize(COIN_QUANTIZER, rounding=ROUND_HALF_UP)

        return ReferralCalculation(
            membership_amount=amount,
            referral_percentage=percentage,
            reward_value=reward_value,
            coin_value=settings_obj.coin_value,
            coins_awarded=coins_awarded,
        )

    @classmethod
    def wallet_for_user(
        cls,
        user,
        *,
        lock: bool = False,
    ) -> MajestianWallet:
        queryset = MajestianWallet.objects

        if lock:
            queryset = queryset.select_for_update()

        try:
            return queryset.get(user=user)
        except MajestianWallet.DoesNotExist:
            try:
                return MajestianWallet.objects.create(user=user)
            except IntegrityError:
                return queryset.get(user=user)

    @classmethod
    @transaction.atomic
    def create_credit(
        cls,
        *,
        user,
        coin_amount: Decimal | str | int | float,
        transaction_type: str,
        description: str,
        status: str = CoinTransaction.Status.POSTED,
        reference_type: str = "",
        reference_id: str = "",
        idempotency_key: str | None = None,
        metadata: dict | None = None,
        available_at=None,
    ) -> CoinTransaction:
        coins = cls.decimal(coin_amount).quantize(
            COIN_QUANTIZER,
            rounding=ROUND_HALF_UP,
        )

        if coins <= 0:
            raise ValidationError("Credit amount must be greater than zero.")

        if idempotency_key:
            existing = CoinTransaction.objects.filter(
                idempotency_key=idempotency_key
            ).first()

            if existing:
                return existing

        settings_obj = cls.economy_settings()
        wallet = cls.wallet_for_user(user, lock=True)

        if wallet.status != MajestianWallet.Status.ACTIVE:
            raise ValidationError(
                "This Majestian Wallet is not active."
            )

        platform_value = (
            coins * settings_obj.coin_value
        ).quantize(MONEY_QUANTIZER, rounding=ROUND_HALF_UP)

        now = timezone.now()

        if status == CoinTransaction.Status.POSTED:
            posted_at = now
        else:
            posted_at = None

        ledger_entry = CoinTransaction.objects.create(
            wallet=wallet,
            transaction_type=transaction_type,
            direction=CoinTransaction.Direction.CREDIT,
            status=status,
            coin_amount=coins,
            coin_value_snapshot=settings_obj.coin_value,
            platform_value=platform_value,
            description=description,
            reference_type=reference_type,
            reference_id=str(reference_id or ""),
            idempotency_key=idempotency_key,
            metadata=metadata or {},
            available_at=available_at,
            posted_at=posted_at,
        )

        if status == CoinTransaction.Status.POSTED:
            MajestianWallet.objects.filter(pk=wallet.pk).update(
                available_coins=F("available_coins") + coins,
                lifetime_earned_coins=F("lifetime_earned_coins") + coins,
                last_transaction_at=now,
            )

        elif status == CoinTransaction.Status.PENDING:
            MajestianWallet.objects.filter(pk=wallet.pk).update(
                pending_coins=F("pending_coins") + coins,
                last_transaction_at=now,
            )

        return ledger_entry

    @classmethod
    @transaction.atomic
    def create_debit(
        cls,
        *,
        user,
        coin_amount: Decimal | str | int | float,
        transaction_type: str,
        description: str,
        reference_type: str = "",
        reference_id: str = "",
        idempotency_key: str | None = None,
        metadata: dict | None = None,
    ) -> CoinTransaction:
        coins = cls.decimal(coin_amount).quantize(
            COIN_QUANTIZER,
            rounding=ROUND_HALF_UP,
        )

        if coins <= 0:
            raise ValidationError("Debit amount must be greater than zero.")

        if idempotency_key:
            existing = CoinTransaction.objects.filter(
                idempotency_key=idempotency_key
            ).first()

            if existing:
                return existing

        settings_obj = cls.economy_settings()
        wallet = cls.wallet_for_user(user, lock=True)
        wallet.refresh_from_db()

        if wallet.status != MajestianWallet.Status.ACTIVE:
            raise ValidationError(
                "This Majestian Wallet is not active."
            )

        if wallet.available_coins < coins:
            raise ValidationError("Insufficient Majestic Coin balance.")

        platform_value = (
            coins * settings_obj.coin_value
        ).quantize(MONEY_QUANTIZER, rounding=ROUND_HALF_UP)

        now = timezone.now()

        ledger_entry = CoinTransaction.objects.create(
            wallet=wallet,
            transaction_type=transaction_type,
            direction=CoinTransaction.Direction.DEBIT,
            status=CoinTransaction.Status.POSTED,
            coin_amount=coins,
            coin_value_snapshot=settings_obj.coin_value,
            platform_value=platform_value,
            description=description,
            reference_type=reference_type,
            reference_id=str(reference_id or ""),
            idempotency_key=idempotency_key,
            metadata=metadata or {},
            posted_at=now,
        )

        updates = {
            "available_coins": F("available_coins") - coins,
            "last_transaction_at": now,
        }

        if transaction_type == CoinTransaction.TransactionType.REDEMPTION:
            updates["lifetime_redeemed_coins"] = (
                F("lifetime_redeemed_coins") + coins
            )

        MajestianWallet.objects.filter(pk=wallet.pk).update(**updates)

        return ledger_entry

    @classmethod
    @transaction.atomic
    def post_pending_transaction(
        cls,
        ledger_entry: CoinTransaction,
    ) -> CoinTransaction:
        entry = (
            CoinTransaction.objects
            .select_for_update()
            .select_related("wallet")
            .get(pk=ledger_entry.pk)
        )

        if entry.status == CoinTransaction.Status.POSTED:
            return entry

        if entry.status != CoinTransaction.Status.PENDING:
            raise ValidationError(
                "Only pending transactions can be posted."
            )

        if entry.available_at and entry.available_at > timezone.now():
            raise ValidationError(
                "This reward is still within its holding period."
            )

        wallet = MajestianWallet.objects.select_for_update().get(
            pk=entry.wallet_id
        )

        if wallet.pending_coins < entry.coin_amount:
            raise ValidationError(
                "Wallet pending balance is lower than the transaction amount."
            )

        now = timezone.now()

        MajestianWallet.objects.filter(pk=wallet.pk).update(
            pending_coins=F("pending_coins") - entry.coin_amount,
            available_coins=F("available_coins") + entry.coin_amount,
            lifetime_earned_coins=(
                F("lifetime_earned_coins") + entry.coin_amount
            ),
            last_transaction_at=now,
        )

        entry.status = CoinTransaction.Status.POSTED
        entry.posted_at = now
        entry.save(update_fields=("status", "posted_at", "updated_at"))

        return entry

    @classmethod
    @transaction.atomic
    def reverse_transaction(
        cls,
        ledger_entry: CoinTransaction,
        *,
        reason: str,
        idempotency_key: str | None = None,
    ) -> CoinTransaction:
        original = (
            CoinTransaction.objects
            .select_for_update()
            .select_related("wallet", "wallet__user")
            .get(pk=ledger_entry.pk)
        )

        if original.status == CoinTransaction.Status.REVERSED:
            try:
                return original.reversal_transaction
            except CoinTransaction.DoesNotExist:
                raise ValidationError(
                    "The transaction is marked reversed but has no reversal entry."
                )

        if original.status != CoinTransaction.Status.POSTED:
            raise ValidationError(
                "Only posted transactions can be reversed."
            )

        wallet = MajestianWallet.objects.select_for_update().get(
            pk=original.wallet_id
        )

        now = timezone.now()

        if original.direction == CoinTransaction.Direction.CREDIT:
            if wallet.available_coins < original.coin_amount:
                raise ValidationError(
                    "The wallet no longer contains enough available coins "
                    "to reverse this credit."
                )

            reversal_direction = CoinTransaction.Direction.DEBIT

            MajestianWallet.objects.filter(pk=wallet.pk).update(
                available_coins=F("available_coins") - original.coin_amount,
                lifetime_reversed_coins=(
                    F("lifetime_reversed_coins") + original.coin_amount
                ),
                last_transaction_at=now,
            )

        else:
            reversal_direction = CoinTransaction.Direction.CREDIT

            MajestianWallet.objects.filter(pk=wallet.pk).update(
                available_coins=F("available_coins") + original.coin_amount,
                last_transaction_at=now,
            )

        reversal = CoinTransaction.objects.create(
            wallet=wallet,
            transaction_type=CoinTransaction.TransactionType.REVERSAL,
            direction=reversal_direction,
            status=CoinTransaction.Status.POSTED,
            coin_amount=original.coin_amount,
            coin_value_snapshot=original.coin_value_snapshot,
            platform_value=original.platform_value,
            description=f"Reversal: {reason}",
            reference_type="CoinTransaction",
            reference_id=str(original.public_id),
            idempotency_key=idempotency_key,
            metadata={
                "original_transaction": str(original.public_id),
                "reason": reason,
            },
            posted_at=now,
            reversal_of=original,
        )

        original.status = CoinTransaction.Status.REVERSED
        original.reversed_at = now
        original.save(
            update_fields=("status", "reversed_at", "updated_at")
        )

        return reversal

    @classmethod
    @transaction.atomic
    def award_recommendation(
        cls,
        recommendation: MajestianRecommendation,
        *,
        place_on_hold: bool | None = None,
    ) -> CoinTransaction:
        recommendation = (
            MajestianRecommendation.objects
            .select_for_update()
            .select_related("referrer", "citizen_level")
            .get(pk=recommendation.pk)
        )

        if recommendation.reward_transaction_id:
            return recommendation.reward_transaction

        economy = cls.economy_settings()

        if not economy.referral_rewards_enabled:
            raise ValidationError(
                "Majestian recommendation rewards are currently disabled."
            )

        if recommendation.fraud_review_required:
            raise ValidationError(
                "This recommendation requires administrator review."
            )

        if economy.require_payment_confirmation:
            allowed_statuses = {
                MajestianRecommendation.Status.PAYMENT_CONFIRMED,
                MajestianRecommendation.Status.REWARD_PENDING,
            }

            if recommendation.status not in allowed_statuses:
                raise ValidationError(
                    "Payment must be confirmed before issuing the reward."
                )

        percentage = recommendation.reward_percentage_snapshot

        if percentage <= 0 and recommendation.citizen_level_id:
            percentage = recommendation.citizen_level.referral_percentage

        calculation = cls.calculate_referral(
            recommendation.membership_amount,
            percentage,
        )

        if place_on_hold is None:
            place_on_hold = economy.reward_hold_days > 0

        if place_on_hold:
            ledger_status = CoinTransaction.Status.PENDING
            available_at = timezone.now() + timedelta(
                days=economy.reward_hold_days
            )
            recommendation_status = (
                MajestianRecommendation.Status.REWARD_PENDING
            )
        else:
            ledger_status = CoinTransaction.Status.POSTED
            available_at = None
            recommendation_status = MajestianRecommendation.Status.REWARDED

        ledger_entry = cls.create_credit(
            user=recommendation.referrer,
            coin_amount=calculation.coins_awarded,
            transaction_type=(
                CoinTransaction.TransactionType.CITIZEN_REFERRAL
            ),
            description=(
                f"{recommendation.get_recommendation_type_display()} "
                f"recommendation reward"
            ),
            status=ledger_status,
            reference_type="MajestianRecommendation",
            reference_id=str(recommendation.public_id),
            idempotency_key=(
                f"recommendation:{recommendation.public_id}"
            ),
            metadata={
                "membership_name": recommendation.membership_name,
                "membership_amount": str(calculation.membership_amount),
                "reward_percentage": str(calculation.referral_percentage),
                "reward_value": str(calculation.reward_value),
                "coin_value": str(calculation.coin_value),
            },
            available_at=available_at,
        )

        recommendation.reward_percentage_snapshot = (
            calculation.referral_percentage
        )
        recommendation.reward_value = calculation.reward_value
        recommendation.coins_awarded = calculation.coins_awarded
        recommendation.reward_transaction = ledger_entry
        recommendation.status = recommendation_status

        if ledger_status == CoinTransaction.Status.POSTED:
            recommendation.rewarded_at = timezone.now()

        recommendation.save(
            update_fields=(
                "reward_percentage_snapshot",
                "reward_value",
                "coins_awarded",
                "reward_transaction",
                "status",
                "rewarded_at",
                "updated_at",
            )
        )

        return ledger_entry

    @classmethod
    def award_referral(
        cls,
        *,
        referrer,
        membership_amount,
        citizen_level: CitizenLevelReward,
        membership_name: str = "",
        referred_user=None,
        payment_reference: str = "",
        payment_confirmed: bool = True,
        place_on_hold: bool | None = None,
        metadata: dict | None = None,
    ) -> MajestianRecommendation:
        status = (
            MajestianRecommendation.Status.PAYMENT_CONFIRMED
            if payment_confirmed
            else MajestianRecommendation.Status.PENDING_PAYMENT
        )

        recommendation = MajestianRecommendation.objects.create(
            referrer=referrer,
            referred_user=referred_user,
            recommendation_type=(
                MajestianRecommendation.RecommendationType.CITIZEN
            ),
            citizen_level=citizen_level,
            membership_name=membership_name,
            membership_amount=membership_amount,
            reward_percentage_snapshot=(
                citizen_level.referral_percentage
            ),
            status=status,
            payment_reference=payment_reference,
            payment_confirmed_at=(
                timezone.now() if payment_confirmed else None
            ),
            metadata=metadata or {},
        )

        if payment_confirmed:
            cls.award_recommendation(
                recommendation,
                place_on_hold=place_on_hold,
            )
            recommendation.refresh_from_db()

        return recommendation
