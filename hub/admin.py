import os
from textwrap import dedent

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
from rest_framework.authtoken.models import Token, TokenProxy
from rest_framework.authtoken.admin import TokenAdmin 

from solo.admin import SingletonModelAdmin
import humanfriendly

from eapi.settings import EVON_VARS, BASE_DIR
import hub.models


admin.site.site_header = "Evon Hub Admin"
admin.site.site_title = "Evon Hub Admin"

admin.site.unregister(TokenProxy)

@admin.register(TokenProxy)
class HubTokenAdmin(TokenAdmin):

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        else:
            return qs.filter(user=request.user)

    def has_module_permission(self, request, obj=None):
        return True

    def has_view_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return True

    def has_save_permission(self, request, obj=None):
        return True

    def has_change_permission(self, request, obj=None):
        return True

    def has_add_permission(self, request, obj=None):
        return True

    def get_changeform_initial_data(self, request):
        if not request.user.is_superuser:
            return {"user": request.user}

    def formfield_for_dbfield(self, db_field, **kwargs):
        request = kwargs.get("request")
        if not request:
            return super().formfield_for_dbfield(db_field, **kwargs)
        formfield = super().formfield_for_dbfield(db_field, **kwargs)
        if not request.user.is_superuser:
            formfield.choices = (c for c in formfield.choices if c[1] == request.user.username)
        return formfield

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_save_and_continue'] = False
        extra_context['show_save_and_add_another'] = False
        return super().changeform_view(request, object_id, form_url, extra_context)


@admin.register(hub.models.OVPNClientConfig)
class OVPNClientAdmin(admin.ModelAdmin):
    view_on_site: bool = False
    actions = None
    custom_template_filename = "openvpn_client_config.html"

    def has_view_permission(self, request, obj=None):
        return True

    def has_add_permission(self, request):
        return True

    def has_module_permission(self, request, obj=None):
        return True

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

        context = {
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
        pass


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

        context = {
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
        pass


@admin.register(hub.models.Rule)
class RuleAdmin(admin.ModelAdmin):
    model = hub.models.Rule
    description = dedent("""
        Define allowed connection sources (Users, Groups, Servers, Server Groups) and destination protocols/ports here.
        Connection destinations (Servers and Server Groups) are controlled when you create a Policy. Rules are effective only when added to Policy.
    """)
    fieldsets = (
        ('Rule', {
            'fields': tuple([f.name for f in model._meta.fields if f.name != "id"] + [f.name for f in model._meta.many_to_many]),
            'description': description
        }),
    )


class RuleInline(admin.TabularInline):
    model = hub.models.Policy.rules.through


@admin.register(hub.models.Policy)
class PolicyAdmin(admin.ModelAdmin):
    list_display = ["name", "description"]
    inlines = [
        RuleInline,
    ]
    model = hub.models.Policy
    description = dedent("""
        Apply Rules to target (destination) Servers and Server Groups here. Rules define allowed connection sources (Users and Servers) and protocols.
    """)
    fieldsets = (
        ('Policy', {
            'fields': tuple([f.name for f in model._meta.fields if f.name != "id"] + [f.name for f in model._meta.many_to_many]),
            'description': description
        }),
    )


@admin.register(hub.models.Config)
class ConfigAdmin(admin.ModelAdmin):

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_save_and_continue'] = False
        extra_context['show_save_and_add_another'] = False
        return super().changeform_view(request, object_id, form_url, extra_context)


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
        return ", ".join(sg.name for sg in obj.server_groups.all() if sg.name != "All Servers")


class ServerInline(admin.TabularInline):
    model = hub.models.Server.server_groups.through


@admin.register(hub.models.ServerGroup)
class ServerGroupAdmin(admin.ModelAdmin):
    inlines = [
        ServerInline,
    ]
    list_display = ["name", "servers"]

    def has_delete_permission(self, request, obj=None):
        if obj and obj.name == "All Servers":
            return False
        return True

    def has_save_permission(self, request, obj=None):
        if obj and obj.name == "All Servers":
            return False
        return True

    def has_change_permission(self, request, obj=None):
        if obj and obj.name == "All Servers":
            return False
        return True

    def servers(self, obj):
        suffix = f'.{EVON_VARS["account_domain"]}'
        if obj.name == "All Servers":
            return "All Servers"
        return ", ".join(s.fqdn.replace(suffix, "") for s in obj.server_set.all())


class UserInLine(admin.TabularInline):
    model = Group.user_set.through
    extra = 0


admin.site.unregister(Group)
@admin.register(Group)
class GenericGroup(GroupAdmin):
    inlines = [UserInLine]
    list_display = ["name", "users"]

    def has_delete_permission(self, request, obj=None):
        if obj and obj.name == "All Users":
            return False
        return True

    def has_save_permission(self, request, obj=None):
        if obj and obj.name == "All Users":
            return False
        return True

    def has_change_permission(self, request, obj=None):
        if obj and obj.name == "All Users":
            return False
        return True

    def users(self, obj):
        if obj.name == "All Users":
            return "All Users"
        return ", ".join(u.username for u in obj.user_set.all())


admin.site.unregister(User)
@admin.register(User)
class GenericUser(UserAdmin):
    list_display = ["username",  "first_name", "last_name", "email", "is_active", "is_superuser", "group_membership"]

    def group_membership(self, obj):
        return ", ".join([g.name for g in obj.groups.all() if g.name != "All Users"])

    def save_model(self, request, obj, form, change):
        if request.user.is_superuser:
            if obj.username != "deployer":
                obj.is_staff = True
                obj.save()
