from auditlog.apps import AuditlogConfig
from django.apps import AppConfig


class HubConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hub"
    verbose_name = "Evon Hub"

    def ready(self):
        from . import signals
        from . import models

        # create All Users group
        group, created = models.Group.objects.update_or_create(
            name="All Users",
        )
        all_users = models.User.objects.all()
        for user in all_users:
            if user not in group.user_set.all():
                user.groups.add(group)

        # create All Servers group
        server_group, created = models.ServerGroup.objects.update_or_create(
            name="All Servers",
        )
        all_servers = models.Server.objects.all()
        for server in all_servers:
            if server not in server_group.server_set.all():
                server.server_groups.add(server_group)


# Example of renaming of 3rd party app in Django Admin
class HubAuditLogConfig(AuditlogConfig):
    verbose_name = "Audit Log"
