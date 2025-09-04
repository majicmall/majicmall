from django.contrib import admin

# Register your models here.
# core/admin.py
from django.contrib import admin
from .models import Merchant, MovieScreen, Movie, Ticket

@admin.register(Merchant)
class MerchantAdmin(admin.ModelAdmin):
    list_display = ("display_name", "user", "plan", "email", "slug")
    search_fields = ("display_name", "slug", "email", "user__username")
    prepopulated_fields = {"slug": ("display_name",)}

admin.site.register(MovieScreen)
admin.site.register(Movie)
admin.site.register(Ticket)
