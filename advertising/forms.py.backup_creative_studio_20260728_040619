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
