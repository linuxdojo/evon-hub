from django.contrib import admin
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.db import models
from django.forms.widgets import Select
from solo.admin import SingletonModelAdmin

import hub.models


@admin.register(hub.models.ServerGroup)
@admin.register(hub.models.Policy)
@admin.register(hub.models.Config)
class ModelAdmin(admin.ModelAdmin):
    pass


@admin.register(hub.models.Server)
class ServerAdmin(admin.ModelAdmin):
    readonly_fields = ('uuid', 'fqdn','ipv4_address', 'connected', 'last_connected')
    list_display = ['fqdn', 'uuid', 'ipv4_address', 'connected', 'last_connected']

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_save'] = False
        extra_context['show_save_and_continue'] = False
        return super().changeform_view(request, object_id, form_url, extra_context)

    def has_add_permission(self, request, obj=None):
        return False
