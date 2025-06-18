from django import forms

class MerchantSignupForm(forms.Form):
    name = forms.CharField(max_length=100)
    email = forms.EmailField()
    logo = forms.ImageField(required=False)
