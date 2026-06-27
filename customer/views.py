from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from merchant.models import Order
from .models import CustomerProfile


@login_required
def dashboard(request):
    profile, created = CustomerProfile.objects.get_or_create(
        user=request.user
    )

    recent_orders = (
        Order.objects.filter(customer_email=request.user.email)
        .order_by("-created_at")[:5]
    )

    pending_orders = recent_orders.filter(status="pending").count()
    paid_orders = recent_orders.filter(status="paid").count()
    shipped_orders = recent_orders.filter(status="shipped").count()
    completed_orders = recent_orders.filter(status="completed").count()

    context = {
        "profile": profile,
        "recent_orders": recent_orders,
        "pending_orders": pending_orders,
        "paid_orders": paid_orders,
        "shipped_orders": shipped_orders,
        "completed_orders": completed_orders,
    }

    return render(
        request,
        "customer/dashboard.html",
        context,
    )