from django.apps import AppConfig


class DropsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "drops"

    def ready(self):
        from . import checks  # noqa: F401
        from . import database  # noqa: F401
