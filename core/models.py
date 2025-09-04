# core/models.py
from django.conf import settings
from django.db import models

# -----------------------------
# 🎥 Movie Screen + Movie Models
# -----------------------------

class MovieScreen(models.Model):
    SCREEN_TYPES = [
        ("Majic", "Majic"),
        ("Nostalgia", "Nostalgia"),
        ("Fantasy", "Fantasy"),
        ("Indie", "Indie"),
        ("Experience", "Experience"),
    ]

    name = models.CharField(max_length=100)                 # e.g., Majic, Nostalgia
    description = models.TextField(blank=True)
    sponsor = models.CharField(max_length=100, null=True, blank=True)
    screen_type = models.CharField(max_length=50, choices=SCREEN_TYPES)
    is_premium = models.BooleanField(default=False)         # VIP access?

    def __str__(self):
        return self.name


class Movie(models.Model):
    screen = models.ForeignKey(MovieScreen, on_delete=models.CASCADE, related_name="movies")

    title = models.CharField(max_length=200)
    description = models.TextField()
    release_date = models.DateField()
    duration = models.IntegerField(help_text="Duration in minutes")
    genre = models.CharField(max_length=100, blank=True)
    runtime = models.CharField(max_length=50, blank=True)
    rating = models.CharField(max_length=10, blank=True)
    trailer_url = models.URLField(blank=True)
    image = models.ImageField(upload_to="movies/", null=True, blank=True)
    is_premiere = models.BooleanField(default=False)
    video = models.FileField(upload_to="movies/videos/", null=True, blank=True)

    def __str__(self):
        return self.title


# -----------------------------
# 🎟️ Ticket Model
# -----------------------------

class Ticket(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True
    )
    session_key = models.CharField(max_length=40, null=True, blank=True)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name="tickets")
    purchased_at = models.DateTimeField(auto_now_add=True)
    used = models.BooleanField(default=False)

    def __str__(self):
        who = "Guest" if not self.user else getattr(self.user, "username", str(self.user))
        return f"Ticket for {self.movie.title} - {who}"


# -----------------------------
# 💼 Merchant Model (Consolidated)
# -----------------------------

class Merchant(models.Model):
    PLAN_CHOICES = [
        ("starter", "Starter"),
        ("pro", "Pro"),
        ("elite", "Elite"),
    ]

    # Use AUTH_USER_MODEL with a stable reverse accessor: user.merchant
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="merchant",
    )

    # Fields used by your onboarding form/templates
    display_name = models.CharField(max_length=255, blank=True)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to="merchant_logos/", blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True)
    website = models.URLField(blank=True)

    # Optional plan & email for business details (keeps your earlier intent)
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default="starter")
    email = models.EmailField(blank=True)

    def __str__(self):
        return self.display_name or f"Merchant #{self.pk}"

    # Backwards-compat convenience if older code expects merchant.name
    @property
    def name(self):
        return self.display_name
