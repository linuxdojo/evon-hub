import ipaddress
from itertools import chain
import json
import os
import re

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.dispatch.dispatcher import receiver
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User, Group
import humanfriendly
from solo.models import SingletonModel
import zoneinfo

from eapi.settings import EVON_VARS
from hub.exceptions import OutOfAddresses
from evon import evon_api
from evon.cli import EVON_API_URL, EVON_API_KEY, inject_pub_ipv4
from evon.log import get_evon_logger


##### Setup globals

logger = get_evon_logger()
FQDN_PATTERN = re.compile(r'(?=^.{4,253}$)(^((?!-)[a-zA-Z0-9-]{1,63}(?<!-)\.)+[a-zA-Z]{2,63}$)')
UUID_PATTERN = re.compile(r'^[a-f0-9]{8}-?[a-f0-9]{4}-?4[a-f0-9]{3}-?[89ab][a-f0-9]{3}-?[a-f0-9]{12}$')
HOSTNAME_PATTERN = re.compile(r"^(?=.{1,255}$)[0-9A-Za-z](?:(?:[0-9A-Za-z]|-){0,61}[0-9A-Za-z])?(?:\.[0-9A-Za-z](?:(?:[0-9A-Za-z]|-){0,61}[0-9A-Za-z])?)*\.?$")


##### Helper Functions

def vpn_ipv4_addresses():
    """
    Produces a list of all available IPv4 addresses that can be assigned to client-side
    OpenVPN connections on the overlay network subnet.
    """
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


def ServerGroupNameValidator(value):
    if "," in value:
        raise ValidationError(
            "Name must not contain commas"
        )


##### Model Classes

class OVPNClientConfig(models.Model):
    # Note: inspired by https://django-etc.readthedocs.io/en/latest/admin.html
    title = _('OpenVPN Client Config Page')
    app_label = 'admin'

    class Meta:
        verbose_name = "OpenVPN Client"
        verbose_name_plural = "OpenVPN Client"

    @classmethod
    def __init_subclass__(cls):
        meta = cls.Meta
        meta.verbose_name = meta.verbose_name_plural = cls.title
        meta.app_label = cls.app_label
        super().__init_subclass__()

    @classmethod
    def register(cls, *, admin_model=None):
        register(cls)(admin_model or cls.bound_admin)

    def save(self):
        pass


class Bootstrap(models.Model):
    # Note: inspired by https://django-etc.readthedocs.io/en/latest/admin.html
    title = _('Bootstrap Page')
    app_label = 'admin'

    class Meta:
        verbose_name = "Bootstrap"
        verbose_name_plural = "Bootstrap"

    @classmethod
    def __init_subclass__(cls):
        meta = cls.Meta
        meta.verbose_name = meta.verbose_name_plural = cls.title
        meta.app_label = cls.app_label
        super().__init_subclass__()

    @classmethod
    def register(cls, *, admin_model=None):
        register(cls)(admin_model or cls.bound_admin)

    def save(self):
        pass


class ServerGroup(models.Model):
    name = models.CharField(
        max_length=200,
        validators=[ServerGroupNameValidator],
    )
    description = models.CharField(max_length=256, blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Server Groups"


class Server(models.Model):
    uuid = models.CharField(
        verbose_name="UUID",
        editable=False,
        max_length=36,
        unique=True,
        validators=[RegexValidator(regex=UUID_PATTERN)],
        help_text=f"This value is set on line 1 of /etc/openvpn/evon.uuid on your endpoint server.",
    )
    # Max fqdn length is 1004 according to RFC, but max mariadb unique varchar is 255
    fqdn = models.CharField(
        verbose_name="FQDN",
        max_length=255,
        unique=True,
        validators=[EvonFQDNValidator],
        editable=False,
        help_text=("This value is set on line 2 of /etc/openvpn/evon.uuid on your endpoint server, "
                   f"with '.{EVON_VARS['account_domain']}' appended. An index is auto added to the first "
                   "name-part for uniqueness if needed. To change this value, edit /etc/openvpn/evon.uuid "
                   "and restart OpenVPN on your endpoint server."
        )
    )
    ipv4_address = models.GenericIPAddressField(
        verbose_name="IPv4 Address",
        editable=False,
        protocol="IPv4",
        validators=[EvonIPV4Validator],
        help_text="This value is auto-assigned and static for this Server"
    )
    # connected and disconnected_since will be auto-updated by mapper.py
    connected = models.BooleanField(
        default=False,
        editable=False
    )
    disconnected_since = models.DateTimeField(
        verbose_name="Disconnected Since",
        blank=True,
        null=True,
        editable=False
    )
    server_groups = models.ManyToManyField(
        ServerGroup,
        blank=True,
        verbose_name="Server Groups"
    )

    def __str__(self):
        return self.fqdn

    def short_name(self):
        suffix = f'.{EVON_VARS["account_domain"]}'
        return self.fqdn.replace(suffix, "")

    def last_seen(self):
        if not self.disconnected_since:
            return "now"
        else:
            delta = timezone.now() - self.disconnected_since
            delta_seconds = round(delta.total_seconds())
            hf_delta = humanfriendly.format_timespan(delta_seconds, detailed=False, max_units=2)
            return f"{hf_delta} ago"

    def user_has_access(self, user):
        """
        returns True if user is permitted to interact with this server instance based on policy, else False
        """
        # get all policies that target this server
        policies_targetting_server = list(
            set(
                chain(
                    # get all policies who specify this server as a target server
                    self.policy_set.all(),
                    # get all policies who have a target server group containing this server
                    Policy.objects.filter(servergroups__in=ServerGroup.objects.filter(server=self))
                )
            )
        )
        # generate unique set of source rules that these policies use
        rules = list(set(chain(*[p.rules.all() for p in policies_targetting_server])))
        # get all users that can access this server
        users_with_access = list(
            set(
                chain(
                    # get all users that are sourced by the set of rules
                    list(chain(*[r.source_users.all() for r in rules])),
                    # get all users that are in groups sourced by the set of rules
                    list(chain(*[g.user_set.all() for g in list(chain(*[r.source_groups.all() for r in rules]))]))
                )
            )
        )
        return user in users_with_access


    def save(self, *args, dev_mode=False, **kwargs):
        # force dev mode if we're not on an AL2 EC2 instance
        if not dev_mode:
            try:
                with open("/etc/os-release") as f:
                    if not "Amazon Linux" in f.read():
                        dev_mode = True
            except:
                dev_mode = True
        # dhcp-style ipv4_address assignment
        if not self.ipv4_address:
            for ipv4_addr in vpn_ipv4_addresses():
                if not Server.objects.filter(ipv4_address=ipv4_addr).first():
                    self.ipv4_address = ipv4_addr
                    break
            else:
                # we're out of addresses, the validator will warn the user
                logger.warning(f"Overlay network is out of addresses!")
        # auto-append account domain to supplied fqdn
        if not self.fqdn.endswith(EVON_VARS["account_domain"]):
            self.fqdn = f"{self.fqdn}.{EVON_VARS['account_domain']}"
        # ensure fqdn is unique by adding appending index into to the first label if necessary
        desired_fqdn = self.fqdn
        index = 0
        while Server.objects.filter(fqdn=self.fqdn).exclude(uuid=self.uuid):
            # bump index
            index += 1
            parts = desired_fqdn.split(".")
            parts[0] = parts[0] + f"-{index}"
            self.fqdn = ".".join(parts)
        # set disconnected_since
        if self.connected:
            self.disconnected_since = None
            # update dns, add record
            payload = {
                "changes": {
                    "new": {self.fqdn: self.ipv4_address},
                    "removed": {},
                    "updated": {},
                    "unchanged": {}
                }
            }
            if not dev_mode:
                payload = inject_pub_ipv4(json.dumps(payload))
                response = evon_api.set_records(EVON_API_URL, EVON_API_KEY, payload)
                logger.info(f"set_records reponse: {response}")
        else:
            self.disconnected_since = timezone.now()
            # update dns, remove record
            payload = {
                "changes": {
                    "new": {},
                    "removed": {self.fqdn: self.ipv4_address},
                    "updated": {},
                    "unchanged": {}
                }
            }
            if not dev_mode:
                payload = inject_pub_ipv4(json.dumps(payload))
                response = evon_api.set_records(EVON_API_URL, EVON_API_KEY, payload)
                logger.info(f"set_records reponse: {response}")
        # validate and save
        self.full_clean()
        super().save(*args, **kwargs)


class Rule(models.Model):
    TCP = "TCP"
    UDP = "UDP"
    ICMP = "ICMP"
    ANY = "ALL"
    PROTOCOLS = (
        (TCP, "TCP"),
        (UDP, "UDP"),
        (ICMP, "ICMP"),
        (ANY, "Any Protocol"),
    )
    name = models.CharField(max_length=200)
    source_users = models.ManyToManyField(
        User,
        blank=True,
        verbose_name="Source Users"
    )
    source_groups = models.ManyToManyField(
        Group,
        blank=True,
        verbose_name="Source Groups"
    )
    source_servers = models.ManyToManyField(
        Server,
        blank=True,
        verbose_name="Source Servers"
    )
    source_servergroups = models.ManyToManyField(
        ServerGroup,
        blank=True,
        verbose_name="Source Server Groups"
    )
    destination_protocol = models.CharField(max_length=4, choices=PROTOCOLS)
    destination_ports = models.CharField(
        max_length=256,
        blank=True,
        null=True,
        help_text="Comma separated port numbers and dashed ranges, eg: 80,443,7000-8000",
    )

    def __str__(self):
        return self.name

    def get_unified_sources(self):
        unified_sources = \
            list(self.source_users.all()) + \
            list(self.source_groups.all()) + \
            list(self.source_servers.all()) + \
            list(self.source_servergroups.all())
        return unified_sources

    class Meta:
        verbose_name_plural = "Rules"


class Policy(models.Model):
    name = models.CharField(max_length=200)
    description = models.CharField(max_length=256, blank=True, null=True)
    rules = models.ManyToManyField(
        Rule,
        blank=True,
        verbose_name="Rules"
    )
    servers = models.ManyToManyField(
        Server,
        blank=True,
        verbose_name="Target Servers"
    )
    servergroups = models.ManyToManyField(
        ServerGroup,
        blank=True,
        verbose_name="Target Server Groups"
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Policies"


class Config(SingletonModel):
    TIMEZONES = ((tzone, tzone) for tzone in sorted(list(zoneinfo.available_timezones())))
    discovery_mode = models.BooleanField(default=True, help_text="Disable to prevent any new Servers from joining your overlay network")
    timezone = models.CharField(max_length=64, choices=TIMEZONES, default="UTC", help_text="Select your local timezone")

    def __str__(self):
        return "Hub Configuration"

    class Meta:
        verbose_name = "Config"
        verbose_name_plural = "Config"
