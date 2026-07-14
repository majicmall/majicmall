from django import forms

from .pickup_models import MerchantPickupAddress


INPUT_CLASS = (
    "w-full rounded-xl border border-zinc-700 bg-zinc-950 "
    "px-4 py-3 text-white outline-none transition "
    "focus:border-yellow-400 focus:ring-2 focus:ring-yellow-400/20"
)


class MerchantPickupAddressForm(forms.ModelForm):
    class Meta:
        model = MerchantPickupAddress

        fields = [
            "address_line_1",
            "address_line_2",
            "city",
            "state",
            "postal_code",
            "pickup_instructions",
        ]

        widgets = {
            "address_line_1": forms.TextInput(
                attrs={
                    "class": INPUT_CLASS,
                    "autocomplete": "street-address",
                    "placeholder": "123 Peachtree Street NW",
                }
            ),
            "address_line_2": forms.TextInput(
                attrs={
                    "class": INPUT_CLASS,
                    "autocomplete": "address-line2",
                    "placeholder": "Suite 200, Rear Entrance, Building B",
                }
            ),
            "city": forms.TextInput(
                attrs={
                    "class": INPUT_CLASS,
                    "autocomplete": "address-level2",
                    "placeholder": "Atlanta",
                }
            ),
            "state": forms.TextInput(
                attrs={
                    "class": INPUT_CLASS,
                    "autocomplete": "address-level1",
                    "placeholder": "Georgia",
                }
            ),
            "postal_code": forms.TextInput(
                attrs={
                    "class": INPUT_CLASS,
                    "autocomplete": "postal-code",
                    "placeholder": "30318",
                }
            ),
            "pickup_instructions": forms.Textarea(
                attrs={
                    "class": INPUT_CLASS,
                    "rows": 5,
                    "placeholder": (
                        "Tell the driver where to park, which entrance "
                        "to use, and who to ask for."
                    ),
                }
            ),
        }

        labels = {
            "address_line_1": "Street Address",
            "address_line_2": "Suite, Unit, Floor, or Building",
            "city": "City",
            "state": "State",
            "postal_code": "ZIP / Postal Code",
            "pickup_instructions": "Driver Pickup Instructions",
        }

    def clean(self):
        cleaned_data = super().clean()

        required_fields = [
            "address_line_1",
            "city",
            "state",
            "postal_code",
        ]

        for field_name in required_fields:
            value = str(cleaned_data.get(field_name) or "").strip()

            if not value:
                self.add_error(
                    field_name,
                    "This field is required for exact driver navigation.",
                )

        return cleaned_data
