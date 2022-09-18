#!/usr/bin/env python

############################
# Evon OpenVPN Auth Script
############################


import os
import sys

import django
os.environ['DJANGO_SETTINGS_MODULE'] = 'eapi.settings'
django.setup()
from openvpn_api.vpn import VPN  # noqa
import requests  # noqa

from hub.models import UUID_PATTERN, Server, Config  # noqa
from hub.log import get_evon_logger  # noqa


logger = get_evon_logger()

exit_codes = {
    "bad_uuidv4_pattern": 1,
    "uuid_already_connected": 2,
    "discovery_disabled": 3,
    "bad_password": 4
}
username = os.environ["username"]
password = os.environ["password"]
config = Config.get_solo()
ec2_id = requests.get("http://169.254.169.254/latest/dynamic/instance-identity/document").json()["instanceId"]

# Start Auth

logger.info(f"validating new Server connection with username: {username}")

if not UUID_PATTERN.match(username):
    logger.warning(f"Denying login for user '{username}': Username is not a valid UUIDv4 string")
    sys.exit(exit_codes["bad_uuidv4_pattern"])

if password != ec2_id:
    logger.warning(f"Denying login for user '{username}': Password does not contain Hub EC2 instanceId")
    sys.exit(exit_codes["bad_password"])

# obtain list of connected uuids
vpn = VPN(unix_socket="/etc/openvpn/server/evon_mgmt_endpoints")
vpn.connect()
connected_uuids = [c.common_name for c in vpn.get_status().routing_table.values()]
vpn.disconnect()
if username in connected_uuids:
    logger.warning(f"Denying login for user '{username}': Server with same UUID already connected")
    sys.exit(exit_codes["uuid_already_connected"])

if not config.discovery_mode and not Server.objects.filter(uuid=username).first():
    logger.warning(f"Denying login for user '{username}': discovery_mode disabled, not accepting new Servers")
    sys.exit(exit_codes["discovery_disabled"])

logger.info(f"Accepting connection for username: {username}")
