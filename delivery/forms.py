import re

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import DeliveryPartner


User = get_user_model()


class DriverSignupForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "First name",
                "autocomplete": "given-name",
            }
        ),
    )

    last_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Last name",
                "autocomplete": "family-name",
            }
        ),
    )

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "Email address",
                "autocomplete": "email",
            }
        ),
    )

    class Meta(UserCreationForm.Meta):
        model = User

        fields = (
            "first_name",
            "last_name",
            "username",
            "email",
            "password1",
            "password2",
        )

        widgets = {
            "username": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Choose a username",
                    "autocomplete": "username",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["password1"].widget.attrs.update(
            {
                "class": "form-control",
                "placeholder": "Create a password",
                "autocomplete": "new-password",
            }
        )

        self.fields["password2"].widget.attrs.update(
            {
                "class": "form-control",
                "placeholder": "Confirm your password",
                "autocomplete": "new-password",
            }
        )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "An account already exists with this email address."
            )

        return email

    def save(self, commit=True):
        user = super().save(commit=False)

        user.first_name = self.cleaned_data["first_name"].strip()
        user.last_name = self.cleaned_data["last_name"].strip()
        user.email = self.cleaned_data["email"].strip().lower()

        if commit:
            user.save()

        return user


class DriverAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Username",
                "autocomplete": "username",
                "autofocus": True,
            }
        )
    )

    password = forms.CharField(
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Password",
                "autocomplete": "current-password",
            }
        ),
    )


class DeliveryPartnerOnboardingForm(forms.ModelForm):
    confirm_address = forms.BooleanField(
        required=True,
        label=(
            "I confirm that this is my current legal residential address."
        ),
        error_messages={
            "required": "You must confirm your residential address."
        },
    )

    contractor_agreement_accepted = forms.BooleanField(
        required=True,
        label=(
            "I have read and agree to the Independent "
            "Contractor Agreement."
        ),
        error_messages={
            "required": (
                "You must accept the Independent Contractor Agreement "
                "to join the MajicMall Megaverse Driver Network."
            )
        },
    )

    class Meta:
        model = DeliveryPartner

        fields = (
            "street_address",
            "address_line_2",
            "city",
            "state",
            "home_zip",
            "current_zip",
            "service_radius_miles",
            "vehicle_type",
            "phone",
            "confirm_address",
            "contractor_agreement_accepted",
        )

        labels = {
            "street_address": "Street Address",
            "address_line_2": "Apartment, Suite, or Unit",
            "city": "City",
            "state": "State",
            "home_zip": "Home ZIP",
            "current_zip": "Current Working ZIP",
            "service_radius_miles": "Service Radius",
            "vehicle_type": "Vehicle Type",
            "phone": "Phone Number",
        }

        help_texts = {
            "current_zip": (
                "Available deliveries will be matched to this working ZIP."
            ),
            "service_radius_miles": (
                "Choose how far you are willing to travel for deliveries."
            ),
        }

        widgets = {
            "street_address": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "123 Peachtree Street",
                    "autocomplete": "address-line1",
                }
            ),
            "address_line_2": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Apartment, suite, or unit",
                    "autocomplete": "address-line2",
                }
            ),
            "city": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Atlanta",
                    "autocomplete": "address-level2",
                }
            ),
            "state": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "GA",
                    "autocomplete": "address-level1",
                    "maxlength": "2",
                }
            ),
            "home_zip": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "30303",
                    "inputmode": "numeric",
                    "autocomplete": "postal-code",
                    "maxlength": "10",
                }
            ),
            "current_zip": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "30303",
                    "inputmode": "numeric",
                    "maxlength": "10",
                }
            ),
            "service_radius_miles": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "1",
                    "max": "100",
                    "step": "1",
                }
            ),
            "vehicle_type": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "404-555-1234",
                    "inputmode": "tel",
                    "autocomplete": "tel",
                }
            ),
        }

    def clean_street_address(self):
        value = self.cleaned_data.get("street_address", "").strip()

        if len(value) < 5:
            raise forms.ValidationError(
                "Enter a complete street address."
            )

        return value

    def clean_city(self):
        value = self.cleaned_data.get("city", "").strip()

        if len(value) < 2:
            raise forms.ValidationError("Enter a valid city.")

        return value.title()

    def clean_state(self):
        value = self.cleaned_data.get("state", "").strip().upper()

        if not re.fullmatch(r"[A-Z]{2}", value):
            raise forms.ValidationError(
                "Enter the two-letter state abbreviation."
            )

        return value

    def clean_home_zip(self):
        return self._clean_zip(
            self.cleaned_data.get("home_zip"),
            "Home ZIP",
        )

    def clean_current_zip(self):
        return self._clean_zip(
            self.cleaned_data.get("current_zip"),
            "Current Working ZIP",
        )

    def clean_service_radius_miles(self):
        radius = self.cleaned_data.get("service_radius_miles")

        if radius is None:
            raise forms.ValidationError("Enter a service radius.")

        if radius < 1 or radius > 100:
            raise forms.ValidationError(
                "Service radius must be between 1 and 100 miles."
            )

        return radius

    def clean_phone(self):
        phone = self.cleaned_data.get("phone", "").strip()
        digits = re.sub(r"\D", "", phone)

        if len(digits) < 10 or len(digits) > 15:
            raise forms.ValidationError(
                "Enter a valid phone number with at least 10 digits."
            )

        return phone

    @staticmethod
    def _clean_zip(value, label):
        value = (value or "").strip()

        if not re.fullmatch(r"\d{5}(?:-\d{4})?", value):
            raise forms.ValidationError(
                f"{label} must be a valid 5-digit ZIP code."
            )

        return value[:5]
