from django.apps import AppConfig


class LabsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.labs"
    label = "labs"

    def ready(self):
        # Wire up post_delete signal for audit pseudonymisation (§9.5 of design doc)
        from . import signals  # noqa: F401
