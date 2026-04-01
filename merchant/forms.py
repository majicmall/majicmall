from __future__ import annotations

from django import forms
from django.forms import ClearableFileInput

from .models import MerchantStore, MerchantPaymentMethod


class StoreForm(forms.ModelForm):
    remove_logo = forms.BooleanField(required=False, label="Remove current logo")

    class Meta:
        model = MerchantStore
        fields = [
            "logo",
            "store_name",
            "slogan",
            "description",
            "category",
            "zone",
            "plan",
            "is_public",
        ]

        widgets = {
            "store_name": forms.TextInput(
                attrs={"class": "w-full rounded-lg bg-gray-800 border border-gray-700 px-3 py-2"}
            ),
            "slogan": forms.TextInput(
                attrs={"class": "w-full rounded-lg bg-gray-800 border border-gray-700 px-3 py-2"}
            ),
            "description": forms.Textarea(
                attrs={"class": "w-full rounded-lg bg-gray-800 border border-gray-700 px-3 py-2", "rows": 4}
            ),
            "category": forms.TextInput(
                attrs={"class": "w-full rounded-lg bg-gray-800 border border-gray-700 px-3 py-2"}
            ),
            "zone": forms.Select(
                attrs={"class": "w-full rounded-lg bg-gray-800 border border-gray-700 px-3 py-2"}
            ),
            "plan": forms.Select(
                attrs={"class": "w-full rounded-lg bg-gray-800 border border-gray-700 px-3 py-2"}
            ),
            "logo": ClearableFileInput(attrs={"class": "text-sm"}),
            "is_public": forms.CheckboxInput(
                attrs={"class": "h-4 w-4 rounded border-gray-600 bg-gray-800"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if "zone" in self.fields:
            self.fields["zone"].queryset = (
                self.fields["zone"]
                .queryset
                .filter(is_active=True)
                .order_by("sort_order", "name")
            )
            self.fields["zone"].required = False

    def save(self, commit: bool = True) -> MerchantStore:
        instance: MerchantStore = super().save(commit=False)

        if self.cleaned_data.get("remove_logo"):
            if instance.logo:
                instance.logo.delete(save=False)
            instance.logo = None

        if commit:
            instance.save()

        return instance


class MerchantPaymentMethodForm(forms.ModelForm):
    credentials = forms.JSONField(
        required=False,
        widget=forms.Textarea(
            attrs={"rows": 6, "class": "text-black rounded px-2 py-2 w-full font-mono"}
        ),
        help_text='Provider credentials (JSON). Example: {"secret_key": "sk_test_...", "webhook_secret": "whsec_..."}',
    )

    class Meta:
        model = MerchantPaymentMethod
        fields = ["provider", "display_name", "mode", "is_active", "is_default", "credentials"]

        widgets = {
            "provider": forms.Select(attrs={"class": "text-black rounded px-2 py-2 w-full"}),
            "display_name": forms.TextInput(attrs={"class": "text-black rounded px-2 py-2 w-full"}),
            "mode": forms.Select(attrs={"class": "text-black rounded px-2 py-2 w-full"}),
            "is_active": forms.CheckboxInput(attrs={"class": "rounded"}),
            "is_default": forms.CheckboxInput(attrs={"class": "rounded"}),
        }

    def clean(self):
        return super().clean()