from django.db import models


class MovieScreen(models.Model):
    SCREEN_TYPES = [
        ("Majic", "Majic"),
        ("Nostalgia", "Nostalgia"),
        ("Fantasy", "Fantasy"),
        ("Indie", "Indie"),
        ("Experience", "Experience"),
    ]

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    sponsor = models.CharField(max_length=100, null=True, blank=True)
    screen_type = models.CharField(max_length=50, choices=SCREEN_TYPES)
    is_premium = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Movie(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    release_date = models.DateField(null=True, blank=True)
    duration = models.IntegerField(help_text="Duration in minutes", null=True, blank=True)
    image = models.ImageField(upload_to="movies/", null=True, blank=True)
    trailer_url = models.URLField(blank=True)
    video_url = models.URLField(blank=True)
    screen = models.ForeignKey(MovieScreen, on_delete=models.CASCADE, related_name="movies")
    genre = models.CharField(max_length=100, blank=True)
    rating = models.CharField(max_length=20, blank=True)
    cast = models.TextField(blank=True)
    sponsor = models.CharField(max_length=150, blank=True)
    is_premiere = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_featured", "-is_premiere", "-created_at"]

    def __str__(self):
        return self.title
