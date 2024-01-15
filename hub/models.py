from itertools import chain
import datetime
import ipaddress
import json
import random
import re
import string
import uuid

from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.dispatch.dispatcher import receiver
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from solo.models import SingletonModel
import humanfriendly
import pytz

from eapi.settings import EVON_VARS
from evon import evon_api
from evon.cli import EVON_API_URL, EVON_API_KEY, inject_pub_ipv4
from evon.log import get_evon_logger
from hub.exceptions import OutOfAddresses, PasskeyError


##### Setup globals

logger = get_evon_logger()
FQDN_PATTERN = re.compile(r'(?=^.{4,253}$)(^((?!-)[a-zA-Z0-9-]{1,63}(?<!-)\.)+[a-zA-Z]{2,63}$)')
UUID_PATTERN = re.compile(r'^[a-f0-9]{8}-?[a-f0-9]{4}-?4[a-f0-9]{3}-?[89ab][a-f0-9]{3}-?[a-f0-9]{12}$')
DEST_PORTSPEC_PATTERN = re.compile(r"^[\s0-9,-]*$")


##### Helper Functions

def vpn_ipv4_addresses(for_users=False):
    """
    Produces a list of all available IPv4 addresses that can be assigned to client-side
    OpenVPN connections on the overlay network subnet.

    if `for_users` == Ture, use the User subnet, else use the Server subnet
    """
    subnet_key = EVON_VARS["subnet_key"]
    if for_users:
        evon_subnet = f"100.{subnet_key}.208.0/20"
    else:
        evon_subnet = f"100.{subnet_key}.224.0/19"
    evon_network = ipaddress.ip_network(evon_subnet)
    client_addresses = [format(s[2]) for s in evon_network.subnets(new_prefix=30)][1:]
    return client_addresses


def generate_random_string(length=32):
    characters = string.ascii_letters + string.digits
    secure_random = random.SystemRandom()  # Use the system's source for better quality randomness
    return ''.join(secure_random.choice(characters) for _ in range(length))


##### Model Validators

def EvonIPV4Validator(value, for_users=False):
    """
    Validate IPv4 Address fields

    if `for_users` == Ture, use the User subnet, else use the Server subnet
    """
    subnet_key = EVON_VARS["subnet_key"]
    if for_users:
        evon_subnet = f"100.{subnet_key}.208.0/20"
    else:
        evon_subnet = f"100.{subnet_key}.224.0/19"
    all_vpn_client_addresses = set(vpn_ipv4_addresses(for_users=for_users))
    used_vpn_client_addresses = set(Server.objects.values_list("ipv4_address", flat=True).distinct())
    available_vpn_client_addresses =  all_vpn_client_addresses.difference(used_vpn_client_addresses)
    if not available_vpn_client_addresses:
        saturatetd_objects = "users" if for_users else "servers"
        raise ValidationError(f"Your overlay network is out of addresses! Consider deleting one or more {saturatetd_objects}.")
    if value not in all_vpn_client_addresses:
        raise ValidationError(
            f"Invalid address - ipv4_address must be the 3rd address within any /30 subnet of {evon_subnet}"
        )


def EvonIPV4UserValidator(value):
    return EvonIPV4Validator(value, for_users=True)


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

    class Meta:
        verbose_name_plural = "Server Groups"

    def __str__(self):
        return self.name


class Server(models.Model):
    uuid = models.CharField(
        verbose_name="UUID",
        editable=False,
        max_length=36,
        unique=True,
        validators=[RegexValidator(regex=UUID_PATTERN)],
        help_text=("This uuid value must be set on line 1 of the evon.uuid file on your connected server. "
                   "A unique static IPv4 address is auto-assigned to any new UUID values seen by the Hub. "
                   "Visible only to superusers."
        ),
    )
    passkey = models.CharField(
        max_length=128,
        blank=True,
        null=True,
        help_text=("This passkey value must be set after the first colon character on line 2 of the evon.uuid file "
                   "on your connected server in the format &lt;hostname&gt;:&lt;passkey&gt;. "
                   "The raw passkey is not stored and there is no way to retrieve it, but it can be changed. "
                   "Leave blank to keep the existing passkey unchanged. Changable ony by superusers."
        )
    )
    # Max fqdn length is 1004 according to RFC, but max mariadb unique varchar is 255
    fqdn = models.CharField(
        verbose_name="FQDN",
        max_length=255,
        unique=True,
        validators=[EvonFQDNValidator],
        editable=False,
        help_text=("This fqdn value is derived using the <hostname> component of line 2 of the evon.uuid file"
                   "on your connected server in the format <hostname>:<passkey>."
                   "An index number may be automatically appended if needed for uniqueness to prevent "
                   "duplicate FQDN's. To change this value, edit your evon.uuid file and restart "
                   "OpenVPN on your endpoint server."
        )
    )
    ipv4_address = models.GenericIPAddressField(
        verbose_name="IPv4 Address",
        editable=False,
        protocol="IPv4",
        validators=[EvonIPV4Validator],
        help_text="This value is auto-assigned and is static for the UUID used by this Server."
    )
    # connected and disconnected_since will be auto-updated by the openvpn connect/disconnect scripts in evon/openvpn_scripts/
    connected = models.BooleanField(
        default=False,
        editable=False,
        help_text="This value is True if the server has a current healthy VPN connection to this Hub."
    )
    disconnected_since = models.DateTimeField(
        verbose_name="Disconnected Since",
        blank=True,
        null=True,
        editable=False,
        help_text="This value is set only when a previously connected server is disconnected for any reason.",
    )
    server_groups = models.ManyToManyField(
        ServerGroup,
        blank=True,
        verbose_name="Server Groups",
        help_text="A list of Server Gropup ID's in which this Server is a member. Visible only to superusers."
    )

    def __str__(self):
        return self.fqdn

    def short_name(self):
        suffix = f'.{EVON_VARS["account_domain"]}'
        return self.fqdn.replace(suffix, "")

    def last_seen(self):
        if not self.disconnected_since:
            if not self.connected:
                return "never"
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

    def encrypt_passkey(self, raw_passkey):
        return make_password(raw_passkey)

    def validate_passkey(self, raw_passkey):
        if not self.passkey:
            logger.warning(f"no passkey set for server: {self}")
            return False
        return check_password(raw_passkey, self.passkey)

    def save(self, *args, dev_mode=False, **kwargs):
        # force dev mode if we're not on an AL2 EC2 instance
        if EVON_VARS["standalone"]:
            dev_mode = True
        # dhcp-style ipv4_address assignment
        if not self.ipv4_address:
            for ipv4_addr in vpn_ipv4_addresses():
                if not Server.objects.filter(ipv4_address=ipv4_addr).first():
                    self.ipv4_address = ipv4_addr
                    break
            else:
                # we're out of addresses, the validator will warn the user
                logger.warning(f"Overlay network is out of server addresses!")
        # auto-append account domain to supplied fqdn
        if not self.fqdn.endswith(EVON_VARS["account_domain"]):
            # XXX consider not appending below and rather dynamically reading each time for easier reconfig of standalone mode's domain suffix
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
                logger.info(f"set_records request: {payload}")
                response = evon_api.set_records(EVON_API_URL, EVON_API_KEY, payload)
                logger.info(f"set_records reponse: {response}")
        elif not self.connected and not self.disconnected_since:
            # this server has been registered but has never connected
            pass
        else:
            # this server was connected but has not disconnected
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
                logger.info(f"set_records request: {payload}")
                response = evon_api.set_records(EVON_API_URL, EVON_API_KEY, payload)
                logger.info(f"set_records reponse: {response}")
        if self._state.adding and not self._state.db:
            # model instance is new
            if not self.uuid:
                # create a uuid if not provided
                logger.info(f"creating new uuid registration for first seen server: {self}")
                self.uuid = uuid.uuid4()
            if not self.passkey:
                logger.info(f"creating new passkey for first seen server: {self}")
                # create initial passkey if not provided, and store it in an ephemeral property on self named passkey_cleartext
                passkey_cleartext = generate_random_string()
                self.passkey = self.encrypt_passkey(passkey_cleartext)
        elif self.passkey and not self.passkey.startswith('pbkdf2_sha256$'):
            # ensure key is hashed if provided as cleartext
            self.passkey = self.encrypt_passkey(self.passkey)
        # TODO enforce complex passkey
        # validate and save
        self.full_clean()
        super().save(*args, **kwargs)
        # provide the autogenerated cleartext password in return response
        if "passkey_cleartext" in locals():
            return passkey_cleartext


class Rule(models.Model):
    # prefix string for iptables chains that reflect this rule
    chain_name_prefix = "evon-rule-"
    # choices for destination_protofol field
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
    # model fields
    name = models.CharField(
        max_length=200,
        help_text="eg. 'Allow web access'"
    )
    source_users = models.ManyToManyField(
        User,
        blank=True,
        verbose_name="Source Users",
        help_text="A list of User ID's that are permitted as sources by this Rule."
    )
    source_groups = models.ManyToManyField(
        Group,
        blank=True,
        verbose_name="Source Groups",
        help_text="A list of Group ID's whose members are permitted as sources by this Rule."
    )
    source_servers = models.ManyToManyField(
        Server,
        blank=True,
        verbose_name="Source Servers",
        help_text="A list of Server ID's that are permitted as sources by this Rule."
    )
    source_servergroups = models.ManyToManyField(
        ServerGroup,
        blank=True,
        verbose_name="Source Server Groups",
        help_text="A list of Server Group ID's whose members are permitted as sources by this Rule."
    )
    destination_protocol = models.CharField(
        max_length=4,
        choices=PROTOCOLS,
        help_text="The destination protocol permitted by this Rule. For unlisted protocols, select 'Any Protocol (ALL)' and filter using your Server's firewall."
    )
    destination_ports = models.CharField(
        max_length=256,
        blank=True,
        default="",
        help_text="Single or comma separated port numbers with dashed ranges are supported, eg: 80,443,7000-8000",
    )

    class Meta:
        verbose_name_plural = "Rules"

    def __str__(self):
        return self.name

    def get_chain_name(self):
        "returns iptables chain name for this rule"
        return f"{self.chain_name_prefix}{self.pk}"

    def get_unified_sources(self):
        unified_sources = \
            list(self.source_users.all()) + \
            list(self.source_groups.all()) + \
            list(self.source_servers.all()) + \
            list(self.source_servergroups.all())
        return unified_sources

    def clean(self):
        # validate destination_ports
        if self.destination_protocol in [self.TCP, self.UDP]:
            if not self.destination_ports:
                raise ValidationError(
                    {'destination_ports': ('At least one port must be specified for destination protocols TCP or UDP')}
                )
        else:
            if self.destination_ports:
                raise ValidationError(
                    {'destination_ports': ('Ports can only be specified for destination protocols TCP or UDP')}
                )
        # validate destination_ports portspec
        if not DEST_PORTSPEC_PATTERN.match(self.destination_ports):
            raise ValidationError(
                {'destination_ports': ('Illegal characters in port specification')}
            )
        if self.destination_ports:
            for portspec in self.destination_ports.split(","):
                port_range = []
                for port in portspec.split("-"):
                    try:
                        int_port = int(port)
                    except ValueError as e:
                        raise ValidationError(
                            {'destination_ports': (f"Malformed port: '{portspec}'")}
                        )
                    if not 0 <= int_port <= 65535:
                        raise ValidationError(
                            {'destination_ports': (f"Port '{port}' is out of range, ports must be between 0 and 65535.")}
                        )
                    port_range.append(int_port)
                if len(port_range) == 2:
                    if not port_range[0] < port_range[1]:
                        raise ValidationError(
                            {'destination_ports': (f"Malformed port range '{portspec}', start port must be less than end port.")}
                        )
                elif len(port_range) > 2:
                    # too many dashes specified
                    raise ValidationError(
                        {'destination_ports': (f"Malformed port range '{portspec}'.")}
                    )


    def save(self, *args, **kwargs):
        # validate and save
        self.full_clean()
        # strip whitespace from portspec, uniquify and sort
        self.destination_ports = ",".join(sorted(list(set(self.destination_ports.replace(" ", "").split(",")))))
        super().save(*args, **kwargs)


class Policy(models.Model):
    name = models.CharField(max_length=200)
    description = models.CharField(max_length=256, blank=True, null=True)
    rules = models.ManyToManyField(
        Rule,
        blank=True,
        verbose_name="Rules",
        help_text="A list of Rule ID's sourced by this Policy."
    )
    servers = models.ManyToManyField(
        Server,
        blank=True,
        verbose_name="Target Servers",
        help_text="A list of Server ID's that are targetted by this Policy."
    )
    servergroups = models.ManyToManyField(
        ServerGroup,
        blank=True,
        verbose_name="Target Server Groups",
        help_text="A list of Server Group ID's whose members are targetted by this Policy."
    )

    class Meta:
        verbose_name_plural = "Policies"

    def __str__(self):
        return self.name


class Config(SingletonModel):
    ec2_iam_role_status = models.BooleanField(
        default=False,
        verbose_name = "EC2 IAM Role Status",
        editable=False,
        help_text="Health status of your EC2 IAM Role. Must be True (green) in order for this Evon Hub to function correctly. If False (red), please SSH to this EC2 instance and run command 'evon --iam-validate'."
    )
    TIMEZONES = ((tzone, tzone) for tzone in pytz.all_timezones)
    timezone = models.CharField(
        max_length=64,
        choices=TIMEZONES,
        default="UTC",
        help_text="Select the local timezone for this Evon Hub server."
    )
    auto_update = models.BooleanField(
        default=True,
        help_text="Automatically apply updates. The WebUI and the Evon API may become unavailable "
                  "for a few minutes during the update process, but connected Users and Servers "
                  "using the overlay network will not be affected."
    )
    auto_update_time = models.TimeField(
        default=datetime.time(20, 0),
        help_text="Specify auto update start time relative to above timezone in 24 hour HH:MM format."
    )
    discovery_mode = models.BooleanField(
        default=True,
        help_text="Disable to prevent any new Servers from joining your overlay network unless its UUID is whitelisted."
    )
    uuid_blacklist = models.TextField(
        null=True,
        blank=True,
        default="",
        verbose_name="UUID blacklist",
        help_text=(
            "Define a comma separated list of Server UUID's that will be disallowed from connecting. Note that any currenty connected "
            "Server with a UUID specified here will be forcibly disconnected and deleted."
        )
    )
    uuid_whitelist = models.TextField(
        null=True,
        blank=True,
        default="",
        verbose_name="UUID whitelist",
        help_text=(
            "Define a comma separated list of future Server UUID's that will allowed to connect even if discovery mode is disabled. "
            "Currently connected servers do not need to be added here as the Hub will always permit existing Server UUID's to connect."
        )
    )

    class Meta:
        verbose_name = "Config"
        verbose_name_plural = "Config"

    def __str__(self):
        return "Hub Configuration"

    def clean(self):
        # validate uuid_blacklist
        if self.uuid_blacklist:
            for uuid in [u.strip() for u in self.uuid_blacklist.split(",")]:
                if not UUID_PATTERN.match(uuid):
                    raise ValidationError(
                        {'uuid_blacklist': (f'Invalid UUID specified: {uuid}')}
                    )
        # validate uuid_whitelist
        if self.uuid_whitelist:
            for uuid in [u.strip() for u in self.uuid_whitelist.split(",")]:
                if not UUID_PATTERN.match(uuid):
                    raise ValidationError(
                        {'uuid_whitelist': (f'Invalid UUID specified: {uuid}')}
                    )


    def save(self, *args, **kwargs):
        # validate and save
        self.full_clean()
        # strip seconds from auto_update_time
        self.auto_update_time = self.auto_update_time.replace(second=0)
        # strip whitespace from uuids in white/blacklists
        uuid_blacklist = [u.strip() for u in self.uuid_blacklist.split(",")]
        uuid_whitelist = [u.strip() for u in self.uuid_whitelist.split(",")]
        self.uuid_blacklist = ",".join(uuid_blacklist)
        self.uuid_whitelist = ",".join(uuid_whitelist)
        # delete servers in uuid_blacklist
        servers_to_delete = Server.objects.filter(uuid__in=uuid_blacklist)
        for s in servers_to_delete:
            s.delete()
        super().save(*args, **kwargs)


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    ipv4_address = models.GenericIPAddressField(
        verbose_name="IPv4 Address",
        editable=False,
        protocol="IPv4",
        validators=[EvonIPV4UserValidator],
        help_text="This value is auto-assigned and static for this User"
    )
    shared = models.BooleanField(
        default=False,
        help_text="Allow other systems to connect to your device. Enabling this option will increment your Hub's Server count (viewable in Hub Config)."
    )

    def __str__(self):
        return "Profile"

    def save(self, *args, **kwargs):
        # dhcp-style ipv4_address assignment
        if not self.ipv4_address:
            for ipv4_addr in vpn_ipv4_addresses(for_users=True):
                if not UserProfile.objects.filter(ipv4_address=ipv4_addr).first():
                    self.ipv4_address = ipv4_addr
                    break
            else:
                # we're out of addresses, the validator will warn the user
                logger.warning(f"Overlay network is out of user addresses!")
        super().save(*args, **kwargs)
