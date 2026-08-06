from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError

from digital_property.models import (
    DigitalProperty,
    LeasePlan,
)

from .models import (
    AdvertisingCreative,
    Campaign,
    CampaignPlacement,
)


class CampaignForm(forms.ModelForm):
    advertising_locations = forms.ModelMultipleChoiceField(
        queryset=DigitalProperty.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Advertising Locations",
        help_text=(
            "Select one or more available billboards, banners, screens, "
            "or other advertising properties."
        ),
    )

    lease_plan = forms.ModelChoiceField(
        queryset=LeasePlan.objects.none(),
        required=False,
        label="Lease Plan",
        help_text=(
            "The selected lease plan must be available for every chosen "
            "advertising location."
        ),
    )

    class Meta:
        model = Campaign
        fields = (
            "name",
            "advertiser_name",
            "description",
            "start_at",
            "end_at",
            "budget",
            "internal_notes",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "internal_notes": forms.Textarea(attrs={"rows": 4}),
            "start_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "end_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
        }

    def __init__(
        self,
        *args,
        user=None,
        submit_action="draft",
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.user = user
        self.submit_action = submit_action

        available = DigitalProperty.objects.filter(
            active=True,
        ).select_related(
            "property_type",
            "mall_zone",
        ).prefetch_related(
            "lease_plans",
        )

        if self.instance and self.instance.pk:
            current_ids = self.instance.placements.values_list(
                "digital_property_id",
                flat=True,
            )

            available = DigitalProperty.objects.filter(
                forms.models.Q(active=True)
                | forms.models.Q(pk__in=current_ids)
            ).select_related(
                "property_type",
                "mall_zone",
            ).prefetch_related(
                "lease_plans",
            )

            placements = self.instance.placements.select_related(
                "lease_plan",
            )

            self.fields["advertising_locations"].initial = [
                placement.digital_property_id
                for placement in placements
            ]

            first_placement = placements.first()

            if first_placement:
                self.fields["lease_plan"].initial = (
                    first_placement.lease_plan_id
                )

        self.fields["advertising_locations"].queryset = available.order_by(
            "display_order",
            "name",
        )

        self.fields["lease_plan"].queryset = LeasePlan.objects.filter(
            active=True,
        ).order_by(
            "display_order",
            "price",
            "name",
        )

        self.fields["start_at"].input_formats = [
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%d %H:%M:%S",
        ]

        self.fields["end_at"].input_formats = [
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%d %H:%M:%S",
        ]

        if self.instance and self.instance.pk:
            if self.instance.start_at:
                self.initial["start_at"] = (
                    self.instance.start_at.strftime("%Y-%m-%dT%H:%M")
                )

            if self.instance.end_at:
                self.initial["end_at"] = (
                    self.instance.end_at.strftime("%Y-%m-%dT%H:%M")
                )

        for field_name, field in self.fields.items():
            existing = field.widget.attrs.get("class", "")

            if isinstance(
                field.widget,
                (
                    forms.CheckboxInput,
                    forms.CheckboxSelectMultiple,
                    forms.RadioSelect,
                ),
            ):
                field.widget.attrs["class"] = (
                    f"{existing} campaign-choice-input"
                ).strip()
            else:
                field.widget.attrs["class"] = (
                    f"{existing} campaign-form-control"
                ).strip()

            field.widget.attrs.setdefault(
                "aria-label",
                field.label or field_name.replace("_", " ").title(),
            )

        self.fields["advertising_locations"].label_from_instance = (
            self.location_label
        )

        self.fields["lease_plan"].label_from_instance = (
            self.lease_plan_label
        )

    @staticmethod
    def location_label(obj):
        zone = obj.mall_zone.name if obj.mall_zone else "Global"

        return (
            f"{obj.property_code} — {obj.name} | "
            f"{obj.get_inventory_tier_display()} | "
            f"{zone} | Minimum ${obj.minimum_spend}"
        )

    @staticmethod
    def lease_plan_label(obj):
        return (
            f"{obj.name} — ${obj.price} "
            f"({obj.get_billing_period_display()})"
        )

    def clean(self):
        cleaned = super().clean()

        locations = cleaned.get("advertising_locations")
        lease_plan = cleaned.get("lease_plan")
        budget = cleaned.get("budget")
        start_at = cleaned.get("start_at")
        end_at = cleaned.get("end_at")

        submitting = self.submit_action == "submit"

        if submitting:
            if not locations:
                self.add_error(
                    "advertising_locations",
                    "Select at least one advertising location.",
                )

            if not lease_plan:
                self.add_error(
                    "lease_plan",
                    "Select a lease plan.",
                )

            if budget is None:
                self.add_error(
                    "budget",
                    "Enter a campaign budget.",
                )

            if not start_at:
                self.add_error(
                    "start_at",
                    "Select a campaign start date and time.",
                )

            if not end_at:
                self.add_error(
                    "end_at",
                    "Select a campaign end date and time.",
                )

        if start_at and end_at and end_at <= start_at:
            self.add_error(
                "end_at",
                "The campaign end must occur after its start.",
            )

        if locations and lease_plan:
            invalid_locations = [
                location
                for location in locations
                if not location.lease_plans.filter(
                    pk=lease_plan.pk,
                ).exists()
            ]

            if invalid_locations:
                names = ", ".join(
                    location.name
                    for location in invalid_locations
                )

                self.add_error(
                    "lease_plan",
                    (
                        "The selected lease plan is unavailable for: "
                        f"{names}."
                    ),
                )

            location_count = locations.count()

            network_minimum = Decimal(location_count * 25)

            property_minimum = max(
                (
                    location.minimum_spend
                    for location in locations
                ),
                default=Decimal("0.00"),
            )

            combined_lease_cost = (
                lease_plan.price * location_count
            )

            required_budget = max(
                network_minimum,
                property_minimum,
                combined_lease_cost,
            )

            self.required_budget = required_budget

            if budget is not None and budget < required_budget:
                self.add_error(
                    "budget",
                    (
                        f"A campaign using {location_count} location"
                        f"{'s' if location_count != 1 else ''} "
                        f"requires at least ${required_budget:.2f}. "
                        "This is the greater of the multi-location "
                        "minimum, property-tier minimum, and combined "
                        "lease cost."
                    ),
                )

        return cleaned

    def save(self, commit=True):
        campaign = super().save(commit=False)

        campaign.status = (
            Campaign.Status.PENDING
            if self.submit_action == "submit"
            else Campaign.Status.DRAFT
        )

        if (
            self.user is not None
            and getattr(self.user, "is_authenticated", False)
            and not campaign.created_by_id
        ):
            campaign.created_by = self.user

        if commit:
            campaign.save()
            self.save_placements(campaign)

        return campaign

    def save_placements(self, campaign):
        locations = self.cleaned_data.get("advertising_locations")
        lease_plan = self.cleaned_data.get("lease_plan")

        if not locations or not lease_plan:
            if self.submit_action == "submit":
                campaign.placements.all().delete()

            return

        selected_ids = list(
            locations.values_list("pk", flat=True)
        )

        campaign.placements.exclude(
            digital_property_id__in=selected_ids,
        ).delete()

        for location in locations:
            placement, created = CampaignPlacement.objects.get_or_create(
                campaign=campaign,
                digital_property=location,
                defaults={
                    "lease_plan": lease_plan,
                    "start_at": campaign.start_at,
                    "end_at": campaign.end_at,
                    "agreed_price": lease_plan.price,
                },
            )

            if not created:
                placement.lease_plan = lease_plan
                placement.start_at = campaign.start_at
                placement.end_at = campaign.end_at
                placement.agreed_price = lease_plan.price
                placement.full_clean()
                placement.save()


class AdvertisingCreativeForm(forms.ModelForm):
    class Meta:
        model = AdvertisingCreative
        exclude = (
            "id",
            "pk",
            "approval_status",
            "review_notes",
            "reviewed_by",
            "reviewed_at",
            "impressions",
            "clicks",
            "created_at",
            "updated_at",
            "created_by",
        )

    def __init__(
        self,
        *args,
        campaign=None,
        user=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.campaign = campaign
        self.user = user

        for name, field in self.fields.items():
            widget = field.widget
            existing = widget.attrs.get("class", "")

            widget.attrs["class"] = (
                f"{existing} creative-input"
            ).strip()

            if name in {
                "description",
                "caption",
                "copy",
                "body",
                "notes",
                "alt_text",
            }:
                widget.attrs.setdefault("rows", 5)

        if campaign is not None and "campaign" in self.fields:
            self.fields["campaign"].initial = campaign
            self.fields["campaign"].widget = forms.HiddenInput()

    def save(self, commit=True, submit_for_review=False):
        instance = super().save(commit=False)

        if self.campaign is not None:
            instance.campaign = self.campaign

        if (
            self.user is not None
            and getattr(self.user, "is_authenticated", False)
            and not instance.created_by_id
        ):
            instance.created_by = self.user

        instance.approval_status = (
            AdvertisingCreative.ApprovalStatus.PENDING
            if submit_for_review
            else AdvertisingCreative.ApprovalStatus.DRAFT
        )

        if commit:
            instance.save()
            self.save_m2m()

        return instance


class DigitalPropertyForm(forms.ModelForm):
    class Meta:
        model = DigitalProperty
        fields = (
            "property_code",
            "name",
            "slug",
            "property_type",
            "mall_zone",
            "lease_plans",
            "description",
            "location_label",
            "inventory_tier",
            "minimum_spend",
            "width",
            "height",
            "supports_image",
            "supports_video",
            "interactive",
            "availability_status",
            "featured",
            "active",
            "display_order",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "lease_plans": forms.CheckboxSelectMultiple,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():
            existing = field.widget.attrs.get("class", "")

            if isinstance(
                field.widget,
                (
                    forms.CheckboxInput,
                    forms.CheckboxSelectMultiple,
                ),
            ):
                field.widget.attrs["class"] = (
                    f"{existing} inventory-choice"
                ).strip()
            else:
                field.widget.attrs["class"] = (
                    f"{existing} inventory-input"
                ).strip()

    def clean_minimum_spend(self):
        amount = self.cleaned_data["minimum_spend"]

        if amount < 0:
            raise ValidationError(
                "Minimum spend cannot be negative."
            )

        return amount
