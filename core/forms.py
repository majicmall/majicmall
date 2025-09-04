# core/forms.py
from django import forms
from django.utils.text import slugify
from .models import Merchant  # make sure Merchant is defined in core.models

class MerchantSignupForm(forms.ModelForm):
    # Not stored on the model; just a required checkbox in the form
    accept_terms = forms.BooleanField(
        required=True,
        label="I agree to the Terms & Conditions",
    )

    class Meta:
        model = Merchant
        fields = [
            "display_name",   # was: name
            "slug",
            "description",
            "logo",           # was: business_logo
            "phone",
            "website",
            "plan",
            "email",
        ]
        widgets = {
            "display_name": forms.TextInput(attrs={"class": "w-full p-2 rounded border"}),
            "slug": forms.TextInput(attrs={"class": "w-full p-2 rounded border", "placeholder": "auto from display name if left blank"}),
            "description": forms.Textarea(attrs={"class": "w-full p-2 rounded border", "rows": 4}),
            "phone": forms.TextInput(attrs={"class": "w-full p-2 rounded border"}),
            "website": forms.URLInput(attrs={"class": "w-full p-2 rounded border"}),
            "plan": forms.Select(attrs={"class": "w-full p-2 rounded border"}),
            "email": forms.EmailInput(attrs={"class": "w-full p-2 rounded border"}),
        }

    def __init__(self, *args, **kwargs):
        # Allow caller to pass plan='starter' and hide the selector
        plan = kwargs.pop("plan", None)
        super().__init__(*args, **kwargs)
        if plan:
            self.fields["plan"].initial = plan
            self.fields["plan"].widget = forms.HiddenInput()

    def clean_slug(self):
        slug = self.cleaned_data.get("slug") or slugify(
            self.cleaned_data.get("display_name") or ""
        )
        if not slug:
            raise forms.ValidationError(
                "Please provide a display name (we’ll auto-generate the slug)."
            )

        qs = Merchant.objects.filter(slug=slug)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("That slug is taken. Try another.")
        return slug


