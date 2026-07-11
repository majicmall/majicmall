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


ALLOWED_DOCUMENT_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "webp",
    "pdf",
}

MAX_VERIFICATION_FILE_SIZE = 10 * 1024 * 1024


def validate_verification_upload(uploaded_file, label):
    if not uploaded_file:
        return uploaded_file

    extension = (
        uploaded_file.name.rsplit(".", 1)[-1].lower()
        if "." in uploaded_file.name
        else ""
    )

    if extension not in ALLOWED_DOCUMENT_EXTENSIONS:
        raise forms.ValidationError(
            f"{label} must be a JPG, PNG, WEBP, or PDF file."
        )

    if uploaded_file.size > MAX_VERIFICATION_FILE_SIZE:
        raise forms.ValidationError(
            f"{label} must be smaller than 10 MB."
        )

    return uploaded_file


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
            "profile_photo",
            "vehicle_make",
            "vehicle_model",
            "vehicle_year",
            "vehicle_color",
            "license_plate",
            "vehicle_photo",
            "driver_license_document",
            "insurance_document",
            "vehicle_registration_document",
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
            "vehicle_type": "Delivery Method",
            "phone": "Phone Number",
            "profile_photo": "Driver Profile Photo",
            "vehicle_make": "Vehicle Make",
            "vehicle_model": "Vehicle Model",
            "vehicle_year": "Vehicle Year",
            "vehicle_color": "Vehicle Color",
            "license_plate": "License Plate",
            "vehicle_photo": "Vehicle Photo",
            "driver_license_document": "Driver License",
            "insurance_document": "Insurance Card or Policy",
            "vehicle_registration_document": "Vehicle Registration",
        }

        help_texts = {
            "current_zip": (
                "Available deliveries will be matched to this working ZIP."
            ),
            "service_radius_miles": (
                "Choose how far you are willing to travel for deliveries."
            ),
            "profile_photo": (
                "Upload a clear, recent photo of yourself."
            ),
            "vehicle_photo": (
                "Upload a clear exterior photo of the delivery vehicle."
            ),
            "driver_license_document": (
                "Accepted formats: JPG, PNG, WEBP, or PDF. Maximum 10 MB."
            ),
            "insurance_document": (
                "Upload current proof of insurance. Maximum 10 MB."
            ),
            "vehicle_registration_document": (
                "Upload current vehicle registration. Maximum 10 MB."
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
            "profile_photo": forms.ClearableFileInput(
                attrs={
                    "class": "form-control file-control",
                    "accept": "image/jpeg,image/png,image/webp",
                }
            ),
            "vehicle_make": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Toyota",
                }
            ),
            "vehicle_model": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Camry",
                }
            ),
            "vehicle_year": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "2022",
                    "min": "1980",
                    "max": "2100",
                }
            ),
            "vehicle_color": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Black",
                }
            ),
            "license_plate": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "ABC1234",
                    "autocomplete": "off",
                }
            ),
            "vehicle_photo": forms.ClearableFileInput(
                attrs={
                    "class": "form-control file-control",
                    "accept": "image/jpeg,image/png,image/webp",
                }
            ),
            "driver_license_document": forms.ClearableFileInput(
                attrs={
                    "class": "form-control file-control",
                    "accept": "image/jpeg,image/png,image/webp,application/pdf",
                }
            ),
            "insurance_document": forms.ClearableFileInput(
                attrs={
                    "class": "form-control file-control",
                    "accept": "image/jpeg,image/png,image/webp,application/pdf",
                }
            ),
            "vehicle_registration_document": forms.ClearableFileInput(
                attrs={
                    "class": "form-control file-control",
                    "accept": "image/jpeg,image/png,image/webp,application/pdf",
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

    def clean_vehicle_year(self):
        year = self.cleaned_data.get("vehicle_year")

        if year is None:
            return year

        if year < 1980 or year > 2100:
            raise forms.ValidationError(
                "Enter a valid vehicle year."
            )

        return year

    def clean_license_plate(self):
        return (
            self.cleaned_data.get("license_plate", "")
            .strip()
            .upper()
        )

    def clean_profile_photo(self):
        return validate_verification_upload(
            self.cleaned_data.get("profile_photo"),
            "Driver profile photo",
        )

    def clean_vehicle_photo(self):
        return validate_verification_upload(
            self.cleaned_data.get("vehicle_photo"),
            "Vehicle photo",
        )

    def clean_driver_license_document(self):
        return validate_verification_upload(
            self.cleaned_data.get("driver_license_document"),
            "Driver license",
        )

    def clean_insurance_document(self):
        return validate_verification_upload(
            self.cleaned_data.get("insurance_document"),
            "Insurance document",
        )

    def clean_vehicle_registration_document(self):
        return validate_verification_upload(
            self.cleaned_data.get(
                "vehicle_registration_document"
            ),
            "Vehicle registration",
        )

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
