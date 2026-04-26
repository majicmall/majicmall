from collections import defaultdict

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.db.models import Case, When, Value, IntegerField
from django.shortcuts import render, redirect, get_object_or_404

from merchant.models import MallZone, MerchantStore
from .forms import MerchantSignupForm, CommunityMemberForm
from .models import Movie, Ticket


# ---------------------------
# 🌍 Global Pages
# ---------------------------

def homepage(request):
    return render(request, "megaverse_home.html")

def grand_reveal(request):
    return render(request, "grand_reveal.html")


def mall_entrance(request):
    return render(request, "home.html")


def mall_home(request):
    return render(request, "mall/majic_home.html")


def launch_splash(request):
    return render(request, "launch_splash.html")


# ---------------------------
# 💼 Merchant Views
# ---------------------------

def merchant_onboard(request):
    selected_plan = request.GET.get("plan", "")

    if request.method == "POST":
        form = MerchantSignupForm(request.POST, request.FILES)
        if form.is_valid():
            merchant = form.save(commit=False)
            merchant.plan = selected_plan
            merchant.save()
            return redirect("merchant-thank-you")
    else:
        form = MerchantSignupForm()

    return render(
        request,
        "merchant/onboard.html",
        {
            "form": form,
            "selected_plan": selected_plan,
        },
    )


def merchant_thank_you(request):
    return render(request, "thank_you.html")


@login_required
def merchant_dashboard(request):
    """
    Multi-store safe dashboard fallback.
    Uses the user's first non-archived store.
    """
    store = request.user.stores.filter(is_archived=False).order_by("created_at").first()

    if not store:
        return redirect("merchant-setup")

    return render(
        request,
        "merchant/dashboard.html",
        {
            "store": store,
            "merchant": store,
        },
    )


def merchant_invite(request):
    return render(request, "merchant/invite.html")


def merchant_tiers(request):
    return render(request, "merchant/tiers.html")


def business_zone(request):
    zone = get_object_or_404(MallZone, slug="business-services-zone", is_active=True)
    stores = zone.stores.filter(is_public=True, is_archived=False).order_by("store_name")

    return render(
        request,
        "mall/zone_live.html",
        {
            "zone": zone,
            "stores": stores,
        },
    )


def music_zone(request):
    return render(request, "mall/zone_placeholder.html", {"zone_name": "Music"})


class MerchantLoginView(LoginView):
    template_name = "merchant/login.html"


def community_signup(request):
    if request.method == "POST":
        form = CommunityMemberForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Welcome to the MajicMall Megaverse Community!")
            return redirect("community-signup")
    else:
        form = CommunityMemberForm()

    return render(request, "community_signup.html", {"form": form})


# ---------------------------
# 🗺️ Mall Directory + Zones
# ---------------------------

def mall_directory(request):
    active_zone = request.GET.get("zone", "").strip()

    zones = list(
        MallZone.objects
        .filter(is_active=True)
        .order_by("sort_order", "name")
    )

    live_stores_qs = (
        MerchantStore.objects
        .select_related("zone")
        .filter(
            is_public=True,
            is_archived=False,
            zone__isnull=False,
            zone__is_active=True,
        )
        .annotate(
            plan_rank=Case(
                When(plan="elite", then=Value(0)),
                When(plan="pro", then=Value(1)),
                default=Value(2),
                output_field=IntegerField(),
            )
        )
        .order_by(
            "zone__sort_order",
            "zone__name",
            "-is_featured",
            "featured_slot",
            "plan_rank",
            "-created_at",
            "store_name",
        )
    )

    if active_zone:
        live_stores_qs = live_stores_qs.filter(zone__slug=active_zone)

    live_stores = list(live_stores_qs)

    stores_by_zone = defaultdict(list)
    for store in live_stores:
        if store.zone_id:
            stores_by_zone[store.zone_id].append(store)

    zone_sections = []
    for zone in zones:
        if active_zone and zone.slug != active_zone:
            continue

        zone_store_pool = stores_by_zone.get(zone.id, [])

        manual_featured = [
            s for s in zone_store_pool
            if s.is_featured and s.featured_slot in [1, 2, 3, 4, 5]
        ]
        manual_featured = sorted(
            manual_featured,
            key=lambda s: (
                s.featured_slot if s.featured_slot is not None else 999,
                s.plan_rank,
                s.store_name.lower(),
            )
        )

        used_ids = {s.id for s in manual_featured}

        fallback_stores = [
            s for s in zone_store_pool
            if s.id not in used_ids
        ]
        fallback_stores = sorted(
            fallback_stores,
            key=lambda s: (s.plan_rank, -s.id, s.store_name.lower())
        )

        featured_stores = (manual_featured + fallback_stores)[:5]
        empty_slots_count = max(0, 5 - len(featured_stores))

        zone_sections.append({
            "zone": zone,
            "stores": featured_stores,
            "empty_slots": range(empty_slots_count),
            "store_count": len(zone_store_pool),
            "has_stores": bool(featured_stores),
        })

    return render(
        request,
        "mall/directory.html",
        {
            "zones": zones,
            "active_zone": active_zone,
            "live_stores": live_stores,
            "zone_sections": zone_sections,
        },
    )


def zone_entry(request, zone_slug):
    """
    Experience layer:
    /zones/<slug>/
    Shows the branded entrance page for a real MallZone.
    """
    zone = get_object_or_404(MallZone, slug=zone_slug, is_active=True)

    return render(
        request,
        "mall/zone_entry.html",
        {
            "zone": zone,
            "zone_name": zone.name,
            "zone_slug": zone.slug,
        },
    )


def zone_interior(request, zone_slug):
    """
    Functional layer:
    /zones/<slug>/inside/
    Shows all public stores assigned to this zone.
    """
    zone = get_object_or_404(MallZone, slug=zone_slug, is_active=True)

    stores = (
        MerchantStore.objects
        .filter(
            zone=zone,
            is_public=True,
            is_archived=False,
        )
        .annotate(
            plan_rank=Case(
                When(plan="elite", then=Value(0)),
                When(plan="pro", then=Value(1)),
                default=Value(2),
                output_field=IntegerField(),
            )
        )
        .order_by(
            "-is_featured",
            "featured_slot",
            "plan_rank",
            "-created_at",
            "store_name",
        )
    )

    return render(
        request,
        "mall/zone_interior.html",
        {
            "zone": zone,
            "zone_name": zone.name,
            "zone_slug": zone.slug,
            "stores": stores,
            "store_count": stores.count(),
        },
    )


# Optional backward-compatible placeholders
def fashion_zone(request):
    return redirect("zone-entry", zone_slug="fashion-zone")


def entertainment_zone(request):
    return redirect("zone-entry", zone_slug="entertainment-zone")


def tech_zone(request):
    return redirect("zone-entry", zone_slug="tech-zone")


def home_zone(request):
    return redirect("zone-entry", zone_slug="home-zone")


def family_zone(request):
    return redirect("zone-entry", zone_slug="family-zone")


def creators_zone(request):
    return redirect("zone-entry", zone_slug="creators-zone")


def luxury_zone(request):
    return redirect("zone-entry", zone_slug="luxury-zone")


def atls_hottest_zone(request):
    return redirect("zone-entry", zone_slug="atls-hottest-zone")


def food_court_zone(request):
    return redirect("zone-entry", zone_slug="food-court-zone")


def learning_zone(request):
    return redirect("zone-entry", zone_slug="learning-zone")


# ---------------------------
# 📺 TV Zone
# ---------------------------

def tv_home(request):
    return render(request, "tv/tv_home.html")


# ---------------------------
# 🎬 Theater Experience
# ---------------------------

def theater_zone(request):
    return render(request, "theater/theater_home.html", {"zone_name": "Theater"})


def theater_entrance(request):
    return render(request, "theater/theater_entrance.html")


def theater_lobby(request):
    return render(request, "theater/theaterlobby.html")


def box_office(request):
    movies = Movie.objects.all()
    return render(request, "theater/box_office.html", {"movies": movies})


def trailer_view(request):
    return render(request, "theater/trailer_view.html")


def coming_soon(request):
    return render(request, "theater/coming_soon.html")


def theater_stream(request):
    movie_id = request.GET.get("id")
    if not movie_id:
        return redirect("box-office")

    user = request.user if request.user.is_authenticated else None

    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key

    has_ticket = Ticket.objects.filter(
        movie_id=movie_id,
        user=user if user else None,
        session_key=None if user else session_key,
    ).exists()

    if not has_ticket:
        return redirect("box-office")

    movie = get_object_or_404(Movie, id=movie_id)
    return render(
        request,
        "theater/theater_stream.html",
        {
            "poster": movie.image.url if getattr(movie, "image", None) else "default_poster.jpg",
            "video": movie.video.url if getattr(movie, "video", None) else "default_video.mp4",
            "movie": movie,
        },
    )


def buy_ticket(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    user = request.user if request.user.is_authenticated else None

    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key

    exists = Ticket.objects.filter(
        movie=movie,
        user=user if user else None,
        session_key=None if user else session_key,
    ).exists()

    if not exists:
        Ticket.objects.create(
            movie=movie,
            user=user if user else None,
            session_key=None if user else session_key,
        )

    return redirect(f"/theater/stream/?id={movie.id}")
