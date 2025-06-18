from .forms import MerchantSignupForm

from django.shortcuts import render, redirect

# Homepage (Entrance)
def homepage(request):
    return render(request, 'home.html')

# Inside Mall View
def mall_home(request):
    return render(request, 'mall/majic_home.html')


# Splash Countdown (Optional)
def launch_splash(request):
    return render(request, 'launch_splash.html')

# Merchant Onboarding
def merchant_onboard(request):
    if request.method == 'POST':
        form = MerchantSignupForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('thank-you')
    else:
        form = MerchantSignupForm()
    return render(request, 'merchant/onboard.html', {'form': form})

# Thank You Page
def merchant_thank_you(request):
    return render(request, 'thank_you.html')

