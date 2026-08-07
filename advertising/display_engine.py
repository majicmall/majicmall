from __future__ import annotations

from collections import Counter
from typing import Any

from django.utils import timezone

from .models import (
    AdvertisingCreative,
    Campaign,
    CampaignPlacement,
)


LIVE_CAMPAIGN_STATUSES = (
    Campaign.Status.ACTIVE,
)

APPROVED_CREATIVE_STATUS = (
    AdvertisingCreative.ApprovalStatus.APPROVED
)


def _creative_media_url(
    creative: AdvertisingCreative,
    request=None,
) -> str:
    url = ""

    if creative.file:
        try:
            url = creative.file.url
        except (ValueError, AttributeError):
            url = ""

    if not url:
        url = creative.external_media_url or ""

    if request is not None and url.startswith("/"):
        return request.build_absolute_uri(url)

    return url


def _creative_payload(
    creative: AdvertisingCreative,
    *,
    display_seconds: int,
    request=None,
) -> dict[str, Any]:
    return {
        "id": creative.pk,
        "title": creative.title,
        "media_type": creative.media_type,
        "media_url": _creative_media_url(
            creative,
            request=request,
        ),
        "destination_url": creative.destination_url or "",
        "headline": creative.headline or creative.title,
        "call_to_action": creative.call_to_action or "",
        "alt_text": creative.alt_text or creative.title,
        "display_seconds": max(int(display_seconds or 10), 1),
    }


def build_billboard_payload(
    *,
    property_code: str,
    request=None,
) -> dict[str, Any]:
    """
    Build the live creative queue for one DigitalProperty.

    Exclusive bookings override rotating bookings. Rotating campaigns
    are repeated in the queue according to positions_reserved, which
    allows campaign budget to increase display frequency.
    """

    now = timezone.now()

    placements = (
        CampaignPlacement.objects
        .select_related(
            "campaign",
            "digital_property",
        )
        .prefetch_related(
            "campaign__creatives",
        )
        .filter(
            digital_property__property_code=property_code,
            campaign__status__in=LIVE_CAMPAIGN_STATUSES,
        )
        .order_by(
            "campaign__created_at",
            "pk",
        )
    )

    placements = [
        placement
        for placement in placements
        if (
            (
                placement.start_at is None
                or placement.start_at <= now
            )
            and (
                placement.end_at is None
                or placement.end_at > now
            )
            and (
                placement.campaign.start_at is None
                or placement.campaign.start_at <= now
            )
            and (
                placement.campaign.end_at is None
                or placement.campaign.end_at > now
            )
        )
    ]

    if not placements:
        return {
            "property_code": property_code,
            "mode": "fallback",
            "display_seconds": 10,
            "items": [],
        }

    digital_property = placements[0].digital_property
    display_seconds = max(
        int(digital_property.display_seconds or 10),
        1,
    )

    exclusive = [
        placement
        for placement in placements
        if placement.booking_mode == "exclusive"
    ]

    selected_placements = (
        exclusive[:1]
        if exclusive
        else placements
    )

    mode = "exclusive" if exclusive else "rotating"
    queue: list[dict[str, Any]] = []

    for placement in selected_placements:
        creatives = (
            placement.campaign.creatives
            .filter(
                approval_status=APPROVED_CREATIVE_STATUS,
                is_enabled=True,
                media_type__in=(
                    AdvertisingCreative.MediaType.BILLBOARD,
                    AdvertisingCreative.MediaType.BANNER,
                    AdvertisingCreative.MediaType.IMAGE,
                    AdvertisingCreative.MediaType.VIDEO,
                ),
            )
            .order_by(
                "priority",
                "created_at",
            )
        )

        eligible_creatives = []

        for creative in creatives:
            if creative.start_at and creative.start_at > now:
                continue

            if creative.end_at and creative.end_at <= now:
                continue

            if not _creative_media_url(creative):
                continue

            eligible_creatives.append(creative)

        if not eligible_creatives:
            continue

        repeat_count = 1

        if mode == "rotating":
            repeat_count = max(
                int(placement.positions_reserved or 1),
                1,
            )

        for repeat_index in range(repeat_count):
            creative = eligible_creatives[
                repeat_index % len(eligible_creatives)
            ]

            payload = _creative_payload(
                creative,
                display_seconds=display_seconds,
                request=request,
            )

            payload.update(
                {
                    "campaign_id": placement.campaign_id,
                    "campaign_name": placement.campaign.name,
                    "placement_id": placement.pk,
                }
            )

            queue.append(payload)

    # Prevent accidental consecutive duplicate creatives where possible.
    if len(queue) > 2:
        reordered = []
        remaining = list(queue)
        previous_id = None

        while remaining:
            next_index = 0

            for index, item in enumerate(remaining):
                if item["id"] != previous_id:
                    next_index = index
                    break

            selected = remaining.pop(next_index)
            reordered.append(selected)
            previous_id = selected["id"]

        queue = reordered

    campaign_counts = Counter(
        item["campaign_id"]
        for item in queue
    )

    return {
        "property_code": property_code,
        "property_name": digital_property.name,
        "mode": mode,
        "display_seconds": display_seconds,
        "rotation_capacity": digital_property.rotation_capacity,
        "queue_size": len(queue),
        "campaign_frequency": dict(campaign_counts),
        "items": queue,
    }
