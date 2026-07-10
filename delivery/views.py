from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import (
    DeliveryPartnerOnboardingForm,
    DriverAuthenticationForm,
    DriverSignupForm,
)
from .models import DeliveryJob, DeliveryPartner


AGREEMENT_VERSION = DeliveryPartner.CONTRACTOR_AGREEMENT_VERSION


def become_driver(request):
    if request.user.is_authenticated:
        partner = DeliveryPartner.objects.filter(
            user=request.user
        ).first()

        if partner and partner.is_ready_for_command_center:
            return redirect("delivery-dashboard")

        if partner:
            return redirect("delivery-onboarding")

    return render(
        request,
        "delivery/become_driver.html",
    )


def driver_signup(request):
    if request.user.is_authenticated:
        partner = DeliveryPartner.objects.filter(
            user=request.user
        ).first()

        if partner and partner.is_ready_for_command_center:
            return redirect("delivery-dashboard")

        return redirect("delivery-onboarding")

    if request.method == "POST":
        form = DriverSignupForm(request.POST)

        if form.is_valid():
            with transaction.atomic():
                user = form.save()

                DeliveryPartner.objects.create(
                    user=user,
                    status="offline",
                    is_active=True,
                )

            login(
                request,
                user,
                backend="django.contrib.auth.backends.ModelBackend",
            )

            messages.success(
                request,
                (
                    "Your driver account has been created. "
                    "Complete your profile to enter the "
                    "Driver Command Center."
                ),
            )

            return redirect("delivery-onboarding")
    else:
        form = DriverSignupForm()

    return render(
        request,
        "delivery/driver_signup.html",
        {
            "form": form,
        },
    )


class DriverLoginView(LoginView):
    template_name = "delivery/driver_login.html"
    authentication_form = DriverAuthenticationForm
    redirect_authenticated_user = True

    def get_success_url(self):
        partner = DeliveryPartner.objects.filter(
            user=self.request.user
        ).first()

        if partner and partner.is_ready_for_command_center:
            return reverse_lazy("delivery-dashboard")

        return reverse_lazy("delivery-onboarding")

    def form_valid(self, form):
        messages.success(
            self.request,
            "Welcome back to the MajicMall Megaverse Driver Network.",
        )

        return super().form_valid(form)


@login_required
@require_POST
def driver_logout(request):
    logout(request)

    messages.success(
        request,
        "You have been signed out of the Driver Command Center.",
    )

    return redirect("delivery-become-driver")


@login_required
def driver_onboarding(request):
    partner, _created = DeliveryPartner.objects.get_or_create(
        user=request.user,
        defaults={
            "status": "offline",
            "is_active": True,
        },
    )

    agreement_was_already_accepted = (
        partner.contractor_agreement_accepted
    )

    if request.method == "POST":
        form = DeliveryPartnerOnboardingForm(
            request.POST,
            instance=partner,
        )

        if form.is_valid():
            with transaction.atomic():
                partner = form.save(commit=False)
                now = timezone.now()

                if not agreement_was_already_accepted:
                    partner.contractor_agreement_accepted_at = now

                partner.contractor_agreement_accepted = True
                partner.contractor_agreement_version = AGREEMENT_VERSION
                partner.onboarding_completed = True
                partner.is_active = True

                if not partner.onboarding_completed_at:
                    partner.onboarding_completed_at = now

                partner.save()

            messages.success(
                request,
                (
                    "Your driver profile is complete. Welcome to the "
                    "MajicMall Megaverse Driver Network."
                ),
            )

            return redirect("delivery-dashboard")
    else:
        form = DeliveryPartnerOnboardingForm(instance=partner)

    return render(
        request,
        "delivery/driver_onboarding.html",
        {
            "form": form,
            "partner": partner,
            "agreement_version": AGREEMENT_VERSION,
        },
    )


@login_required
def dashboard(request):
    partner = DeliveryPartner.objects.filter(
        user=request.user
    ).first()

    available_jobs = DeliveryJob.objects.none()
    active_delivery_jobs = DeliveryJob.objects.none()
    completed_delivery_jobs = DeliveryJob.objects.none()

    pending_jobs = 0
    active_jobs = 0
    completed_jobs = 0

    if partner and partner.is_ready_for_command_center:
        available_jobs_qs = DeliveryJob.objects.none()

        if partner.status == "available" and partner.current_zip:
            available_jobs_qs = DeliveryJob.objects.filter(
                status="pending",
                partner__isnull=True,
                delivery_zip=partner.current_zip,
            )

        pending_jobs = available_jobs_qs.count()

        available_jobs = available_jobs_qs.select_related(
            "order",
            "store",
        ).order_by("-created_at")[:20]

        active_delivery_jobs = DeliveryJob.objects.filter(
            partner=partner,
            status__in=[
                "accepted",
                "picked_up",
                "out_for_delivery",
            ],
        ).select_related(
            "order",
            "store",
        ).order_by("-created_at")

        active_jobs = active_delivery_jobs.count()

        completed_jobs_qs = DeliveryJob.objects.filter(
            partner=partner,
            status="delivered",
        )

        completed_jobs = completed_jobs_qs.count()

        completed_delivery_jobs = completed_jobs_qs.select_related(
            "order",
            "store",
        ).order_by(
            "-delivered_at",
            "-created_at",
        )[:20]

    return render(
        request,
        "delivery/dashboard.html",
        {
            "partner": partner,
            "pending_jobs": pending_jobs,
            "active_jobs": active_jobs,
            "completed_jobs": completed_jobs,
            "available_jobs": available_jobs,
            "active_delivery_jobs": active_delivery_jobs,
            "completed_delivery_jobs": completed_delivery_jobs,
        },
    )
