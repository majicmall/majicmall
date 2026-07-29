from django.db import models


class PropertyType(models.Model):
    """
    Types of digital real estate inside MajicMall Megaverse.
    """

    name = models.CharField(max_length=100, unique=True)

    description = models.TextField(blank=True)

    active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Property Type"
        verbose_name_plural = "Property Types"

    def __str__(self):
        return self.name
