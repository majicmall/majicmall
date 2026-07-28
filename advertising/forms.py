from .models import AdvertisingCreative
from django import forms

from .models import Campaign


class CampaignForm(forms.ModelForm):
    """
    Model-aware form that automatically supports the existing Campaign model.

    Fields are generated from the model so the form remains compatible as
    campaign capabilities expand.
    """

    class Meta:
        model = Campaign
        fields = "__all__"
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
            "description": forms.Textarea(attrs={"rows": 5}),
            "notes": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name, field in self.fields.items():
            existing_class = field.widget.attrs.get("class", "")

            if isinstance(
                field.widget,
                (
                    forms.CheckboxInput,
                    forms.CheckboxSelectMultiple,
                    forms.RadioSelect,
                ),
            ):
                field.widget.attrs["class"] = (
                    f"{existing_class} campaign-choice-input"
                ).strip()
            else:
                field.widget.attrs["class"] = (
                    f"{existing_class} campaign-form-control"
                ).strip()

            field.widget.attrs.setdefault(
                "aria-label",
                field.label or field_name.replace("_", " ").title(),
            )

class AdvertisingCreativeForm(forms.ModelForm):
    """
    Model-aware Creative Studio form.

    It automatically uses editable fields available on the current
    AdvertisingCreative model while omitting system-managed fields.
    """

    class Meta:
        model = AdvertisingCreative
        exclude = (
            "id",
            "pk",
            "created_at",
            "updated_at",
            "modified_at",
            "created_by",
            "updated_by",
        )
        widgets = {}

    def __init__(self, *args, campaign=None, user=None, **kwargs):
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

    def save(self, commit=True):
        instance = super().save(commit=False)

        if self.campaign is not None and hasattr(instance, "campaign_id"):
            instance.campaign = self.campaign

        if (
            self.user is not None
            and getattr(self.user, "is_authenticated", False)
        ):
            if hasattr(instance, "created_by_id") and not instance.created_by_id:
                instance.created_by = self.user

            if hasattr(instance, "updated_by_id"):
                instance.updated_by = self.user

        if commit:
            instance.save()
            self.save_m2m()

        return instance

