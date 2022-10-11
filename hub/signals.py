from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate
from django.contrib.auth.models import User, Group
from django.contrib.auth.signals import user_logged_in
from django.core.signals import request_started
from django.core.exceptions import PermissionDenied
from django.db.models.signals import pre_delete, post_save
from django.dispatch import receiver
from django.utils import timezone
from rest_framework.authtoken.models import Token
import zoneinfo

from eapi.settings import EVON_VARS
from hub.models import Server, ServerGroup, Config, UserProfile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    # every new user gets an api token and gets added to All Users group
    if created:
        # create token
        Token.objects.create(user=instance)
        # create a user profile
        UserProfile.objects.create(user=instance)
        # add to group
        all_users_group = Group.objects.get(name="All Users")
        instance.groups.add(all_users_group)


@receiver(post_save, sender=Server)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        all_servers_group = ServerGroup.objects.get(name="All Servers")
        instance.server_groups.add(all_servers_group)


@receiver(pre_delete, sender=Group)
def delete_group(sender, instance, **kwargs):
    if instance.name == "All Users":
        raise PermissionDenied


@receiver(pre_delete, sender=ServerGroup)
def delete_server_group(sender, instance, **kwargs):
    if instance.name == "All Servers":
        raise PermissionDenied


@receiver(pre_delete, sender=User)
def delete_user(sender, instance, **kwargs):
    """
    Ensure admin and deployer are immutable
    """
    if instance.username in ["admin", "deployer"]:
        raise PermissionDenied


@receiver(user_logged_in)
def post_login(sender, user, request, **kwargs):
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
    """
    Ensure correct timezone is set
    """
    tzname = Config.get_solo().timezone
    timezone.activate(zoneinfo.ZoneInfo(tzname))
