from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from digital_property.models import DigitalProperty

from .models import Campaign


@dataclass
class CampaignSyncResult:
    scheduled: int = 0
    activated: int = 0
    completed: int = 0
    inventory_updated: int = 0


def property_has_other_open_placements(
    digital_property,
    *,
    exclude_campaign_id=None,
):
    queryset = digital_property.campaign_placements.filter(
        campaign__status__in=[
            Campaign.Status.APPROVED,
            Campaign.Status.SCHEDULED,
            Campaign.Status.ACTIVE,
        ],
    )

    if exclude_campaign_id is not None:
        queryset = queryset.exclude(
            campaign_id=exclude_campaign_id,
        )

    return queryset.exists()


def refresh_property_status(
    digital_property,
    *,
    save=True,
):
    """
    Rotation-aware inventory status.

    Exclusive active booking:
        leased

    Rotating active booking with remaining capacity:
        available

    Fully occupied rotating property:
        leased

    Scheduled booking:
        reserved
    """

    open_placements = (
        digital_property.campaign_placements
        .select_related("campaign")
        .filter(
            campaign__status__in=[
                Campaign.Status.APPROVED,
                Campaign.Status.SCHEDULED,
                Campaign.Status.ACTIVE,
            ],
        )
    )

    exclusive_active = open_placements.filter(
        campaign__status=Campaign.Status.ACTIVE,
        booking_mode="exclusive",
    ).exists()

    exclusive_reserved = open_placements.filter(
        campaign__status__in=[
            Campaign.Status.APPROVED,
            Campaign.Status.SCHEDULED,
        ],
        booking_mode="exclusive",
    ).exists()

    rotating_active_positions = sum(
        placement.positions_reserved
        for placement in open_placements.filter(
            campaign__status=Campaign.Status.ACTIVE,
            booking_mode="rotating",
        )
    )

    rotating_reserved_positions = sum(
        placement.positions_reserved
        for placement in open_placements.filter(
            campaign__status__in=[
                Campaign.Status.APPROVED,
                Campaign.Status.SCHEDULED,
            ],
            booking_mode="rotating",
        )
    )

    total_positions = (
        rotating_active_positions
        + rotating_reserved_positions
    )

    if exclusive_active:
        new_status = "leased"
    elif exclusive_reserved:
        new_status = "reserved"
    elif total_positions >= digital_property.rotation_capacity:
        new_status = "leased"
    elif rotating_reserved_positions:
        new_status = "reserved"
    else:
        new_status = "available"

    if digital_property.availability_status != new_status:
        digital_property.availability_status = new_status

        if save:
            digital_property.save(
                update_fields=["availability_status"],
            )

        return True

    return False


def refresh_campaign_inventory(campaign):
    updated = 0

    properties = DigitalProperty.objects.filter(
        campaign_placements__campaign=campaign,
    ).distinct()

    for digital_property in properties:
        if refresh_property_status(digital_property):
            updated += 1

    return updated


@transaction.atomic
def approve_campaign(
    campaign,
    *,
    reviewed_by,
    review_notes="",
):
    """
    Approve a campaign and reserve its selected inventory.
    """

    if not campaign.placements.exists():
        raise ValueError(
            "A campaign must have at least one placement "
            "before approval."
        )

    if not campaign.creatives.exists():
        raise ValueError(
            "A campaign must have at least one creative "
            "before approval."
        )

    if not campaign.start_at or not campaign.end_at:
        raise ValueError(
            "Campaign dates are required before approval."
        )

    now = timezone.now()

    campaign.status = (
        Campaign.Status.ACTIVE
        if campaign.start_at <= now < campaign.end_at
        else Campaign.Status.SCHEDULED
    )

    if campaign.start_at > now:
        campaign.status = Campaign.Status.SCHEDULED

    campaign.reviewed_by = reviewed_by
    campaign.reviewed_at = now
    campaign.approved_at = now
    campaign.review_notes = review_notes
    campaign.save(
        update_fields=[
            "status",
            "reviewed_by",
            "reviewed_at",
            "approved_at",
            "review_notes",
            "updated_at",
        ],
    )

    refresh_campaign_inventory(campaign)

    return campaign


@transaction.atomic
def reject_campaign(
    campaign,
    *,
    reviewed_by,
    review_notes,
):
    campaign.status = Campaign.Status.REJECTED
    campaign.reviewed_by = reviewed_by
    campaign.reviewed_at = timezone.now()
    campaign.review_notes = review_notes
    campaign.save(
        update_fields=[
            "status",
            "reviewed_by",
            "reviewed_at",
            "review_notes",
            "updated_at",
        ],
    )

    refresh_campaign_inventory(campaign)

    return campaign


@transaction.atomic
def request_campaign_changes(
    campaign,
    *,
    reviewed_by,
    review_notes,
):
    campaign.status = Campaign.Status.CHANGES_REQUESTED
    campaign.reviewed_by = reviewed_by
    campaign.reviewed_at = timezone.now()
    campaign.review_notes = review_notes
    campaign.save(
        update_fields=[
            "status",
            "reviewed_by",
            "reviewed_at",
            "review_notes",
            "updated_at",
        ],
    )

    refresh_campaign_inventory(campaign)

    return campaign


@transaction.atomic
def sync_campaign_states(now=None):
    """
    Advance approved advertising campaigns according to their dates.

    Scheduled → Active
    Active → Completed
    Approved → Scheduled or Active
    """

    if now is None:
        now = timezone.now()

    result = CampaignSyncResult()

    approved_campaigns = Campaign.objects.filter(
        status=Campaign.Status.APPROVED,
    )

    for campaign in approved_campaigns:
        if campaign.end_at and campaign.end_at <= now:
            campaign.status = Campaign.Status.COMPLETED
            result.completed += 1
        elif campaign.start_at and campaign.start_at <= now:
            campaign.status = Campaign.Status.ACTIVE
            result.activated += 1
        else:
            campaign.status = Campaign.Status.SCHEDULED
            result.scheduled += 1

        campaign.save(
            update_fields=["status", "updated_at"],
        )

        result.inventory_updated += (
            refresh_campaign_inventory(campaign)
        )

    scheduled_campaigns = Campaign.objects.filter(
        status=Campaign.Status.SCHEDULED,
        start_at__lte=now,
    )

    for campaign in scheduled_campaigns:
        if campaign.end_at and campaign.end_at <= now:
            campaign.status = Campaign.Status.COMPLETED
            result.completed += 1
        else:
            campaign.status = Campaign.Status.ACTIVE
            result.activated += 1

        campaign.save(
            update_fields=["status", "updated_at"],
        )

        result.inventory_updated += (
            refresh_campaign_inventory(campaign)
        )

    active_campaigns = Campaign.objects.filter(
        status=Campaign.Status.ACTIVE,
        end_at__lte=now,
    )

    for campaign in active_campaigns:
        campaign.status = Campaign.Status.COMPLETED
        campaign.save(
            update_fields=["status", "updated_at"],
        )

        result.completed += 1
        result.inventory_updated += (
            refresh_campaign_inventory(campaign)
        )

    return result
