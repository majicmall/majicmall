from django.apps import AppConfig


class MajestianEconomyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "majestian_economy"
    verbose_name = "Majestic Economy"

    def ready(self):
        # Importing these modules activates wallet signals, seed data,
        # and Majestic Economy system checks.
        from . import checks  # noqa: F401
        from . import signals  # noqa: F401
