"""
MajicMall Megaverse merchant membership service.

Membership activation, anniversaries, plan history and Majestic Coin
transactions must pass through this service.
"""

from datetime import date, datetime

from django.db import transaction
from django.utils import timezone

from .models import (
    MajesticCoinTransaction,
    MajesticCoinWallet,
    MerchantMembership,
    MerchantMembershipHistory,
)


FOUNDATION_WELCOME_COINS = 100


def add_one_year(value):
    """
    Add one calendar year.

    February 29 becomes February 28 when the following year is not
    a leap year.
    """
    try:
        return value.replace(year=value.year + 1)
    except ValueError:
        return value.replace(
            year=value.year + 1,
            month=2,
            day=28,
        )


def next_anniversary(member_since, today=None):
    """
    Calculate the next membership anniversary on or after today.
    """
    today = today or timezone.localdate()

    if isinstance(member_since, datetime):
        original_date = timezone.localtime(member_since).date()
    else:
        original_date = member_since

    try:
        anniversary = date(
            today.year,
            original_date.month,
            original_date.day,
        )
    except ValueError:
        anniversary = date(today.year, 2, 28)

    if anniversary < today:
        try:
            anniversary = anniversary.replace(
                year=anniversary.year + 1
            )
        except ValueError:
            anniversary = anniversary.replace(
                year=anniversary.year + 1,
                month=2,
                day=28,
            )

    return anniversary


def build_foundation_member_number(membership):
    return f"FM-{membership.pk:06d}"


@transaction.atomic
def award_coins(
    user,
    amount,
    reason,
    reference,
    transaction_type=MajesticCoinTransaction.TYPE_AWARD,
):
    """
    Add or deduct Majestic Coins exactly once per unique reference.
    """
    amount = int(amount)

    wallet, _ = (
        MajesticCoinWallet.objects
        .select_for_update()
        .get_or_create(
            owner=user,
            defaults={"balance": 0},
        )
    )

    existing = MajesticCoinTransaction.objects.filter(
        reference=reference,
    ).first()

    if existing:
        return wallet, existing, False

    new_balance = wallet.balance + amount

    if new_balance < 0:
        raise ValueError("Majestic Coin balance cannot be negative.")

    wallet.balance = new_balance
    wallet.save(update_fields=["balance", "updated_at"])

    record = MajesticCoinTransaction.objects.create(
        wallet=wallet,
        amount=amount,
        transaction_type=transaction_type,
        reason=reason,
        reference=reference,
        balance_after=new_balance,
    )

    return wallet, record, True


def record_membership_history(
    membership,
    change_type,
    previous_plan="",
    new_plan="",
    previous_status="",
    new_status="",
    note="",
):
    return MerchantMembershipHistory.objects.create(
        membership=membership,
        change_type=change_type,
        previous_plan=previous_plan or "",
        new_plan=new_plan or "",
        previous_status=previous_status or "",
        new_status=new_status or "",
        effective_date=timezone.now(),
        note=note or "",
    )


@transaction.atomic
def activate_membership(
    user,
    store,
    plan,
    foundation_pass_verified=False,
):
    """
    Create or update the merchant's permanent membership.

    Foundation Merchant benefits:
    - Vision-equivalent benefits
    - Complimentary for one calendar year
    - Scheduled transition to Vision
    - One-time 100 Majestic Coins award
    """
    normalized_plan = str(plan or "vision").strip().lower()

    allowed_plans = {
        choice[0]
        for choice in MerchantMembership.PLAN_CHOICES
    }

    if normalized_plan not in allowed_plans:
        normalized_plan = MerchantMembership.PLAN_VISION

    now = timezone.now()
    today = timezone.localdate()

    membership = (
        MerchantMembership.objects
        .select_for_update()
        .filter(owner=user)
        .first()
    )

    created = membership is None

    if created:
        membership = MerchantMembership(
            owner=user,
            primary_store=store,
            current_plan=normalized_plan,
            status=(
                MerchantMembership.STATUS_FOUNDATION
                if normalized_plan
                == MerchantMembership.PLAN_FOUNDATION
                else MerchantMembership.STATUS_ACTIVE
            ),
            member_since=now,
            anniversary_date=add_one_year(today),
            last_plan_change_at=now,
        )

        previous_plan = ""
        previous_status = ""
    else:
        previous_plan = membership.current_plan
        previous_status = membership.status

        membership.primary_store = store or membership.primary_store
        membership.anniversary_date = next_anniversary(
            membership.member_since,
            today=today,
        )

        if previous_plan != normalized_plan:
            membership.previous_plan = previous_plan
            membership.last_plan_change_at = now

    membership.current_plan = normalized_plan

    if normalized_plan == MerchantMembership.PLAN_FOUNDATION:
        foundation_end = add_one_year(today)

        membership.status = MerchantMembership.STATUS_FOUNDATION
        membership.is_foundation_member = True
        membership.foundation_pass_verified = bool(
            foundation_pass_verified
        )
        membership.foundation_expires_on = foundation_end
        membership.complimentary_until = foundation_end
        membership.next_billing_date = foundation_end
        membership.renewal_date = foundation_end
        membership.transition_plan = MerchantMembership.PLAN_VISION
    else:
        membership.status = MerchantMembership.STATUS_ACTIVE

        if not membership.next_billing_date:
            membership.next_billing_date = add_one_year(today)

        if not membership.renewal_date:
            membership.renewal_date = membership.next_billing_date

    membership.save()

    if (
        normalized_plan == MerchantMembership.PLAN_FOUNDATION
        and not membership.foundation_member_number
    ):
        membership.foundation_member_number = (
            build_foundation_member_number(membership)
        )
        membership.save(
            update_fields=[
                "foundation_member_number",
                "updated_at",
            ]
        )

    if store and hasattr(store, "plan"):
        if store.plan != normalized_plan:
            store.plan = normalized_plan
            store.save(update_fields=["plan"])

    if created:
        change_type = MerchantMembershipHistory.CHANGE_CREATED
    elif previous_plan != normalized_plan:
        change_type = MerchantMembershipHistory.CHANGE_ADMIN
    else:
        change_type = MerchantMembershipHistory.CHANGE_STATUS

    if (
        created
        or previous_plan != normalized_plan
        or previous_status != membership.status
    ):
        record_membership_history(
            membership=membership,
            change_type=change_type,
            previous_plan=previous_plan,
            new_plan=membership.current_plan,
            previous_status=previous_status,
            new_status=membership.status,
            note=(
                "Foundation Merchant membership activated."
                if normalized_plan
                == MerchantMembership.PLAN_FOUNDATION
                else "Merchant membership activated or updated."
            ),
        )

    if (
        normalized_plan == MerchantMembership.PLAN_FOUNDATION
        and not membership.majestic_coins_awarded
    ):
        wallet, coin_record, awarded = award_coins(
            user=user,
            amount=FOUNDATION_WELCOME_COINS,
            reason="Foundation Merchant Welcome Award",
            reference=f"foundation-welcome-{membership.pk}",
        )

        membership.majestic_coins_awarded = True

        if not membership.majestic_coins_awarded_at:
            membership.majestic_coins_awarded_at = (
                coin_record.created_at or timezone.now()
            )

        membership.save(
            update_fields=[
                "majestic_coins_awarded",
                "majestic_coins_awarded_at",
                "updated_at",
            ]
        )

    return membership
