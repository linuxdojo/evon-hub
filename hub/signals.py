from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in
from django.core.exceptions import PermissionDenied
from django.db.models.signals import pre_delete, post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token

from eapi.settings import EVON_VARS

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created and instance.username in ["admin", "deployer"]:
        Token.objects.create(user=instance)


@receiver(pre_delete, sender=User)
def delete_user(sender, instance, **kwargs):
    """
    Ensure admin and deployer are immutable
    """
    #XXX this produces an empty 403 Forbidden page. Consider how to improve it.
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
