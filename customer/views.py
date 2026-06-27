from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from merchant.models import Order
from .models import CustomerProfile


@login_required
def dashboard(request):
    profile, created = CustomerProfile.objects.get_or_create(
        user=request.user
    )

    orders = Order.objects.filter(
        customer_email=request.user.email
    ).order_by("-created_at")

    recent_orders = orders[:5]

    context = {
        "profile": profile,
        "recent_orders": recent_orders,
        "pending_orders": orders.filter(status="pending").count(),
        "paid_orders": orders.filter(status="paid").count(),
        "shipped_orders": orders.filter(shipping_status="shipped").count(),
        "completed_orders": orders.filter(status="completed").count(),
    }

    return render(
        request,
        "customer/dashboard.html",
        context,
    )