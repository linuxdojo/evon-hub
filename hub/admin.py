from django.contrib import admin
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.db import models
from django.forms.widgets import Select
from django.utils import timezone
from solo.admin import SingletonModelAdmin
import humanfriendly

import hub.models


@admin.register(hub.models.Policy)
class PolicyAdmin(admin.ModelAdmin):
    pass


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
