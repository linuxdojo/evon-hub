import os

from django.contrib import admin
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.auth.models import User, Group
from django.db import models
from django.forms.widgets import Select
from django.http import HttpRequest, HttpResponse
from django.utils import timezone
from django.urls import path
from django.template import Context
from django.template import Template
from solo.admin import SingletonModelAdmin
import humanfriendly

from eapi.settings import EVON_VARS, BASE_DIR
import hub.models


admin.site.site_header = "Evon Hub Admin"
admin.site.site_title = "Evon Hub Admin"


@admin.register(hub.models.Bootstrap)
class BootstrapAdmin(admin.ModelAdmin):
    view_on_site: bool = False
    actions = None
    custom_template_filename = "bootstrap.html"

    def has_add_permission(self, request):
        return True

    def has_module_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return False

    def get_urls(self):
        meta = self.model._meta
        patterns = [path(
            '',
            self.admin_site.admin_view(self.view_custom),
            name=f'{meta.app_label}_{meta.model_name}_changelist'
        )]
        return patterns

    def view_custom(self, request):
        custom_context = {
            "account_domain": EVON_VARS["account_domain"],
            "deploy_token": User.objects.get(username="deployer").auth_token,
        }
        template_path = os.path.join(f"{BASE_DIR}", "hub", "templates", "hub", self.custom_template_filename)
        with open(template_path) as f:
            custom_template = f.read()
        template = Template(custom_template)
        context = Context(custom_context)
        custom_content = template.render(context)

        context: dict = {
            'show_save': False,
            'show_save_and_continue': False,
            'show_save_and_add_another': False,
            'title': self.model._meta.verbose_name,
            'custom_content': custom_content,
        }
        return self._changeform_view(request, object_id=None, form_url='', extra_context=context)

    def response_add(self, request, obj, post_url_continue=None):
        return HttpResponseRedirect(request.path)

    def save_model(self, request, obj, form, change):
        obj.bound_request = request
        obj.bound_admin = self
        obj.save()



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
