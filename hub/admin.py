from django.contrib import admin
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.auth.models import User, Group
from django.db import models
from django.forms.widgets import Select
from django.utils import timezone
from etc.admin import CustomModelPage, admins
from solo.admin import SingletonModelAdmin
import humanfriendly

from eapi.settings import EVON_VARS
import hub.models


class BootstrapPage(CustomModelPage):
    title = "Evon Bootstrap"
    bound_admin = admins.CustomPageModelAdmin  # set admin class for this page


@admin.register(BootstrapPage)
class BootstrapPageModelAdmin(admins.ReadonlyAdmin):
    pass

@admin.register(hub.models.Policy)
class PolicyAdmin(admin.ModelAdmin):
    list_display = ["name", "description"]


@admin.register(hub.models.Config)
class ConfigAdmin(admin.ModelAdmin):
    pass


@admin.register(hub.models.Server)
class ServerAdmin(admin.ModelAdmin):
    readonly_fields = ('uuid', 'fqdn','ipv4_address', 'connected', 'disconnected_since', 'last_seen')
    list_display = ['fqdn', 'uuid', 'ipv4_address', 'connected', 'disconnected_since', 'last_seen', 'groups']

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_save'] = True
        extra_context['show_save_and_continue'] = False
        return super().changeform_view(request, object_id, form_url, extra_context)

    def has_add_permission(self, request, obj=None):
        return False

    def last_seen(self, obj):
        if not obj.disconnected_since:
            return "now"
        else:
            delta = timezone.now() - obj.disconnected_since
            delta_seconds = round(delta.total_seconds())
            hf_delta = humanfriendly.format_timespan(delta_seconds, detailed=False, max_units=2)
            return f"{hf_delta} ago"

    def groups(self, obj):
        return ", ".join(sg.name for sg in obj.server_groups.all())


class ServerInline(admin.TabularInline):
    model = hub.models.Server.server_groups.through


@admin.register(hub.models.ServerGroup)
class ServerGroupAdmin(admin.ModelAdmin):
    inlines = [
        ServerInline,
    ]
    list_display = ["name", "servers"]

    def servers(self, obj):
        suffix = f'.{EVON_VARS["account_domain"]}'
        return ", ".join(s.fqdn.replace(suffix, "") for s in obj.server_set.all())


class UserInLine(admin.TabularInline):
    model = Group.user_set.through
    extra = 0


admin.site.unregister(Group)
@admin.register(Group)
class GenericGroup(GroupAdmin):
    inlines = [UserInLine]
    list_display = ["name", "users"]

    def users(self, obj):
        return ", ".join(u.username for u in obj.user_set.all())


admin.site.unregister(User)
@admin.register(User)
class GenericUser(UserAdmin):
    list_display = ["username",  "first_name", "last_name", "email", "is_active", "is_superuser", "group_membership"]

    def group_membership(self, obj):
        return ", ".join([g.name for g in obj.groups.all()])

    def save_model(self, request, obj, form, change):
        if request.user.is_superuser:
            if obj.username != "deployer":
                obj.is_staff = True
                obj.save()
