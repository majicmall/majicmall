from django import forms
from django.utils.text import slugify
from .models import Merchant


class MerchantSignupForm(forms.ModelForm):
    accept_terms = forms.BooleanField(
        required=True,
        label="I agree to the Terms & Conditions",
    )

    class Meta:
        model = Merchant
        fields = [
            "display_name",
            "slug",
            "description",
            "logo",
            "phone",
            "website",
            "plan",
            "email",
        ]
        widgets = {
            "display_name": forms.TextInput(
                attrs={
                    "class": "w-full rounded-xl bg-white/10 border border-white/20 px-4 py-3 text-white placeholder-gray-300",
                    "placeholder": "Business / Brand Name",
                }
            ),
            "slug": forms.TextInput(
                attrs={
                    "class": "w-full rounded-xl bg-white/10 border border-white/20 px-4 py-3 text-white placeholder-gray-300",
                    "placeholder": "auto from display name if left blank",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "w-full rounded-xl bg-white/10 border border-white/20 px-4 py-3 text-white placeholder-gray-300",
                    "rows": 4,
                    "placeholder": "Tell us about your store or brand",
                }
            ),
            "logo": forms.ClearableFileInput(
                attrs={"class": "block w-full text-sm text-white"}
            ),
            "phone": forms.TextInput(
                attrs={
                    "class": "w-full rounded-xl bg-white/10 border border-white/20 px-4 py-3 text-white placeholder-gray-300",
                    "placeholder": "Business phone number",
                }
            ),
            "website": forms.URLInput(
                attrs={
                    "class": "w-full rounded-xl bg-white/10 border border-white/20 px-4 py-3 text-white placeholder-gray-300",
                    "placeholder": "https://yourwebsite.com",
                }
            ),
            "plan": forms.Select(
                attrs={"class": "w-full rounded-xl bg-white/10 border border-white/20 px-4 py-3 text-white"}
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "w-full rounded-xl bg-white/10 border border-white/20 px-4 py-3 text-white placeholder-gray-300",
                    "placeholder": "Business email address",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        plan = kwargs.pop("plan", None)
        super().__init__(*args, **kwargs)

        if plan:
            self.fields["plan"].initial = plan
            self.fields["plan"].widget = forms.HiddenInput()

        self.fields["accept_terms"].widget.attrs.update(
            {"class": "h-4 w-4 rounded border-white/30 bg-white/10"}
        )

    def clean_slug(self):
        slug = self.cleaned_data.get("slug") or slugify(
            self.cleaned_data.get("display_name") or ""
        )
        if not slug:
            raise forms.ValidationError(
                "Please provide a display name so we can generate your store slug."
            )

        qs = Merchant.objects.filter(slug=slug)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("That slug is taken. Try another.")
        return slug