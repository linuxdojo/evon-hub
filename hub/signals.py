from functools import partial

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate
from django.contrib.auth.signals import user_logged_in
from django.core.exceptions import PermissionDenied
from django.core.signals import request_started
from django.db import transaction
from django.db.models.signals import pre_save, pre_delete, post_delete, post_save, post_migrate, m2m_changed
from django.dispatch import receiver
from django.utils import timezone
from rest_framework.authtoken.models import Token
import zoneinfo

from evon.log import get_evon_logger
from eapi.settings import EVON_VARS
from hub import firewall
import hub.models


logger = get_evon_logger()


###############################
##### pre_save events
###############################

@receiver(pre_save, sender=hub.models.User)
def pre_save_user(sender, instance, **kwargs):
    "prevent mutation of the admin and deployer users"

    # make necessary attributes of admin and deployer immutable
    if instance.pk == 1:
        instance.username = "admin"
        instance.is_superuser = True
        instance.is_staff = True
        instance.active = True
    elif instance.pk == 2:
        instance.username = "deployer"
        instance.is_superuser = False
        instance.is_staff = False
        instance.active = True


###############################
##### post_save events
###############################

@receiver(post_save, sender=hub.models.User)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    "create token and add new users to all users group"

    # every new user gets an api token and gets added to All Users group
    if created:
        # create token
        Token.objects.create(user=instance)
        # create a user profile
        hub.models.UserProfile.objects.create(user=instance)
        # add to group
        all_users_group = hub.models.Group.objects.get(name="All Users")
        instance.groups.add(all_users_group)
        # we need to update any rules using the "All Users" group.
        rules = hub.models.Rule.objects.filter(source_groups__in=[all_users_group])
        for rule in rules:
            transaction.on_commit(partial(firewall.apply_rule, rule))

    if not instance.is_active:
        # disconnect the user from the VPN if connected
        transaction.on_commit(partial(firewall.kill_inactive_users, extra_user=instance.username))


@receiver(post_save, sender=hub.models.Group)
def upsert_group(sender, instance=None, created=False, **kwargs):
    """
    Update iptables rules for any Rule that references this Group
    """
    rules = hub.models.Rule.objects.filter(source_groups__in=[instance])
    for rule in rules:
        transaction.on_commit(partial(firewall.apply_rule, rule))


@receiver(post_save, sender=hub.models.Server)
def add_server_to_all_servers_group(sender, instance=None, created=False, **kwargs):
    "add new servers to the all servers group"

    if created:
        all_servers_group = hub.models.ServerGroup.objects.get(name="All Servers")
        instance.server_groups.add(all_servers_group)
        # we need to update any rules or policies using the "All Servers" group.
        rules = hub.models.Rule.objects.filter(source_servergroups__in=[all_servers_group])
        for rule in rules:
            transaction.on_commit(partial(firewall.apply_rule, rule))
        policies = hub.models.Policy.objects.filter(servergroups__in=[all_servers_group])
        for policy in policies:
            transaction.on_commit(partial(firewall.apply_policy, policy))


@receiver(post_save, sender=hub.models.ServerGroup)
def upsert_servergroup(sender, instance=None, created=False, **kwargs):
    """
    Update iptables rules for any Rule or Policy that references this ServerGroup
    """
    rules = hub.models.Rule.objects.filter(source_servergroups__in=[instance])
    for rule in rules:
        transaction.on_commit(partial(firewall.apply_rule, rule))
    policies = hub.models.Policy.objects.filter(servergroups__in=[instance])
    for policy in policies:
        transaction.on_commit(partial(firewall.apply_policy, policy))


@receiver(post_save, sender=hub.models.Rule)
def upsert_rule(sender, instance=None, created=False, **kwargs):
    "upsert iptables chain for Rule"

    firewall.apply_rule(instance)


@receiver(post_save, sender=hub.models.Policy)
def upsert_policy(sender, instance=None, created=False, **kwargs):
    "upsert iptables rules for Policy"

    firewall.apply_policy(instance)


###############################
##### pre_delete events
###############################

@receiver(pre_delete, sender=hub.models.Group)
def delete_group(sender, instance, **kwargs):
    "prevent deletion of the all users group"

    if instance.name == "All Users":
        raise PermissionDenied


@receiver(pre_delete, sender=hub.models.ServerGroup)
def delete_server_group(sender, instance, **kwargs):
    "prevent deletion of the all servers group"

    if instance.name == "All Servers":
        raise PermissionDenied


@receiver(pre_delete, sender=hub.models.User)
def delete_user(sender, instance, **kwargs):
    "prevent deletion of admin and deployer users"

    if instance.pk in [1, 2]:
        # disallow deletion of admin or deployer user
        raise PermissionDenied


###############################
##### post_delete events
###############################

@receiver(post_delete)
def delete_object(sender, instance=None, **kwargs):
    """
    Update fw rules on object deletions
    """
    if isinstance(instance, hub.models.Rule):
        firewall.delete_rule(instance)
        return

    if isinstance(instance, hub.models.Policy):
        firewall.delete_policy(instance)
        return

    if isinstance(instance, hub.models.Server):
        transaction.on_commit(firewall.kill_orphan_servers)

    # just re-init if a user, group, server, servergroup, etc is deleted
    transaction.on_commit(firewall.init)


###############################
##### m2m_changed events
###############################

@receiver(m2m_changed)
def update_object(sender, instance=None, created=False, **kwargs):
    "update iptables for Rules and Policies"

    if isinstance(instance, hub.models.Rule):
        firewall.apply_rule(instance)
    elif isinstance(instance, hub.models.Policy):
        firewall.apply_policy(instance)
    else:
        transaction.on_commit(firewall.init)


###############################
##### other events
###############################

@receiver(user_logged_in)
def post_login(sender, user, request, **kwargs):
    "add warning alert for admin user if using default admin login password"

    # warn admin user to change their default password
    if user.username == "admin":
        ec2_id = EVON_VARS["ec2_id"]
        if authenticate(username='admin', password=ec2_id):
            messages.warning(
                request,
                f"You are currently using the default admin password. Please navigate to your profile page to change it."
            )


@receiver(request_started)
def new_request(sender, environ, **kwargs):
    "Ensure correct timezone is set"

    tzname = hub.models.Config.get_solo().timezone
    timezone.activate(zoneinfo.ZoneInfo(tzname))


@receiver(post_migrate)
def create_default_groups(sender, **kwargs):
    "create default groups during db migrations"

    if sender.name == "hub":
        # create All Users group
        group, created = hub.models.Group.objects.update_or_create(
            name="All Users",
        )
        all_users = hub.models.User.objects.all()
        for user in all_users:
            if user not in group.user_set.all():
                user.groups.add(group)

        # create All Servers group
        server_group, created = hub.models.ServerGroup.objects.update_or_create(
            name="All Servers",
        )
        all_servers = hub.models.Server.objects.all()
        for server in all_servers:
            if server not in server_group.server_set.all():
                server.server_groups.add(server_group)
