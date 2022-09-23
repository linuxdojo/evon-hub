from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db.models.signals import pre_delete, post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)


@receiver(pre_delete, sender=User)
def delete_user(sender, instance, **kwargs):
    """
    Ensure admin and deployer are immutable
    """
    #TODO this produces an empty 403 Forbidden page. Consider how to improve it.
    if instance.username in ["admin", "deployer"]:
        raise PermissionDenied
