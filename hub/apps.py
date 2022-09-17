from django.apps import AppConfig
from auditlog.apps import AuditlogConfig


class HubConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hub"
    verbose_name = "Evon Hub"

    def ready(self):
        from . import signals


# Example of renaming of 3rd party app in Django Admin
class HubAuditLogConfig(AuditlogConfig):
    verbose_name = "Audit Log"
