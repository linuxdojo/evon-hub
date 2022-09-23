import ipaddress
import os
import re

from django.core.validators import RegexValidator
from django.db import models
from django.dispatch.dispatcher import receiver
from django.core.exceptions import ValidationError
from django.utils import timezone
from solo.models import SingletonModel

from eapi.settings import EVON_VARS
from hub.exceptions import OutOfAddresses


##### Setup globals

FQDN_PATTERN = re.compile(r'(?=^.{4,253}$)(^((?!-)[a-zA-Z0-9-]{1,63}(?<!-)\.)+[a-zA-Z]{2,63}$)')
UUID_PATTERN = re.compile(r'^[a-f0-9]{8}-?[a-f0-9]{4}-?4[a-f0-9]{3}-?[89ab][a-f0-9]{3}-?[a-f0-9]{12}$')
HOSTNAME_PATTERN = re.compile(r"^(?=.{1,255}$)[0-9A-Za-z](?:(?:[0-9A-Za-z]|-){0,61}[0-9A-Za-z])?(?:\.[0-9A-Za-z](?:(?:[0-9A-Za-z]|-){0,61}[0-9A-Za-z])?)*\.?$")


##### Helper Functions

def vpn_ipv4_addresses():
    subnet_key = EVON_VARS["subnet_key"]
    evon_subnet = f"100.{subnet_key}.224.0/19"
    evon_network = ipaddress.ip_network(evon_subnet)
    client_addresses = [format(s[2]) for s in evon_network.subnets(new_prefix=30)][1:]
    return client_addresses


##### Model Validators

def EvonIPV4Validator(value):
    subnet_key = EVON_VARS["subnet_key"]
    evon_subnet = f"100.{subnet_key}.224.0/19"
    all_vpn_client_addresses = set(vpn_ipv4_addresses())
    used_vpn_client_addresses = set(Server.objects.values_list("ipv4_address", flat=True).distinct())
    available_vpn_client_addresses =  all_vpn_client_addresses.difference(used_vpn_client_addresses)
    if not available_vpn_client_addresses:
        raise ValidationError("Your overlay network is out of addresses! Consider deleting one or more servers.")
    if value not in all_vpn_client_addresses:
        raise ValidationError(
            f"Invalid address - ipv4_address must be the 3rd address within any /30 subnet of {evon_subnet}"
        )


def EvonFQDNValidator(value):
    if not FQDN_PATTERN.match(value):
        raise ValidationError(
            "Please provide a valid FQDN"
        )
    evon_account_domain = EVON_VARS["account_domain"]
    if not value.lower().endswith(evon_account_domain):
        raise ValidationError(
            f"Provided FQDN must end with '.{evon_account_domain}'"
        )


##### Model Classes

class Server(models.Model):
    uuid = models.CharField(
        max_length=36,
        unique=True,
        validators=[RegexValidator(regex=UUID_PATTERN)],
    )
    ipv4_address = models.GenericIPAddressField(
        protocol="IPv4",
        validators=[EvonIPV4Validator]
    )
    # Max fqdn length is 1004 according to RFC, but max mariadb unique varchar is 255
    fqdn = models.CharField(
        max_length=255,
        unique=True,
        validators=[EvonFQDNValidator],
    )
    # connected and last_connected will be auto-updated by mapper.py
    connected = models.BooleanField(default=False, editable=False)
    last_connected = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.fqdn

    def save(self, *args, **kwargs):
        if not self.ipv4_address:
            for ipv4_addr in vpn_ipv4_addresses():
                if not Server.objects.filter(ipv4_address=ipv4_addr).first():
                    self.ipv4_address = ipv4_addr
                    break
            else:
                # we're out of addresses, the validator will warn the user
                logger.warning(f"Overlay network is out of addresses!")
        if not self.fqdn.endswith(EVON_VARS["account_domain"]):
            # auto-append account domain to supplied fqdn
            self.fqdn = f"{self.fqdn}.{EVON_VARS['account_domain']}"
        # validate and save
        self.full_clean()
        super().save(*args, **kwargs)


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
