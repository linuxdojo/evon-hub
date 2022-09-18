import ipaddress
import os
import re
import yaml

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch.dispatcher import receiver
from django.core.exceptions import ValidationError
from solo.models import SingletonModel

from eapi.settings import BASE_DIR


##### Setup globals

FQDN_PATTERN = re.compile(r'(?=^.{4,253}$)(^((?!-)[a-zA-Z0-9-]{1,63}(?<!-)\.)+[a-zA-Z]{2,63}$)')
UUID_PATTERN = re.compile(r'^[a-f0-9]{8}-?[a-f0-9]{4}-?4[a-f0-9]{3}-?[89ab][a-f0-9]{3}-?[a-f0-9]{12}$')
with open(os.path.join(BASE_DIR, "evon-vars.yaml")) as f:
    evon_vars = yaml.safe_load(f)


##### Model Validators

def EvonIPV4Validator(value):
    subnet_key = evon_vars["subnet_key"]
    evon_subnet = f"100.{subnet_key}.224.0/19"
    if not ipaddress.ip_address(value) in ipaddress.ip_network(evon_subnet):
        raise ValidationError(
            f"IPv4 address must be in subnet {evon_subnet}"
        )


def EvonFQDNValidator(value):
    if not FQDN_PATTERN.match(value):
        raise ValidationError(
            "Please provide a valid FQDN"
        )
    evon_account_domain = evon_vars["account_domain"]
    if not value.lower().endswith(evon_account_domain):
        raise ValidationError(
            f"Provided FQDN must end with '.{evon_account_domain}'"
        )


##### Model Classes

class Server(models.Model):
    # Max fqdn length is 1004 according to RFC, but max mariadb unique varchar is 255
    ipv4_address = models.GenericIPAddressField(
        protocol="IPv4",
        validators=[EvonIPV4Validator]
    )
    fqdn = models.CharField(
        max_length=255,
        unique=True,
        validators=[EvonFQDNValidator],
    )
    uuid = models.CharField(
        max_length=36,
        unique=True,
        validators=[RegexValidator(regex=UUID_PATTERN)],
    )
    connected = models.BooleanField(default=False, editable=False)

    def __str__(self):
        return self.fqdn


class ServerGroup(models.Model):
    name = models.CharField(max_length=200)
    create_date = models.DateTimeField('date created')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Server Groups"


class Policy(models.Model):
    name = models.CharField(max_length=200)
    create_date = models.DateTimeField('date created')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Policies"


class Config(SingletonModel):
    discovery_mode = models.BooleanField(default=True, help_text="Disable to prevent any new Servers from joining your overlay network")

    def __str__(self):
        return "Hub Configuration"

    class Meta:
        verbose_name = "Config"
        verbose_name_plural = "Config"


##### Signal handlers

@receiver(pre_delete, sender=User)
def delete_user(sender, instance, **kwargs):
    """
    Ensure admin and deployer are immutable
    """
    if instance.username in ["admin", "deployer"]:
        raise PermissionDenied
