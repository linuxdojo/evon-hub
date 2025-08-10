#!/opt/evon-hub/.env/bin/python

##################################
# Evon OpenVPN Server Auth Script
##################################


import os
import sys
import pwd

if os.getuid() and pwd.getpwuid(os.getuid())[0] == "openvpn":
    os.execl("/usr/bin/sudo", "-i", sys.argv[0], os.environ["username"], os.environ["password"])

import evon
import django
os.environ['DJANGO_SETTINGS_MODULE'] = 'eapi.settings'
django.setup()
from hub.models import Server, Config, vpn_ipv4_addresses  # noqa
from evon.log import get_evon_logger  # noqa


logger = get_evon_logger()
username = os.environ.get("username") or sys.argv[1]
password = os.environ.get("password") or sys.argv[2]
config = Config.get_solo()


logger.info(f"Authenticating new Server connection with UUID: {username}")

if username in config.uuid_blacklist.split(","):
    logger.warning(f"Denying login for UUID '{username}': UUID is blacklisted in Hub Config.")
    sys.exit(1)

if not config.discovery_mode:
    # if uuid is not associated with a current server, and username is not whitelisted
    if not Server.objects.filter(uuid=username).first() and username not in config.uuid_whitelist.split(","):
        logger.warning(f"Denying login for UUID '{username}': discovery_mode is disabled and UUID is not known nor whitelisted.")
        sys.exit(2)

server_count = Server.objects.count()
max_server_count = len(vpn_ipv4_addresses())
if server_count == max_server_count:
    logger.error(f"Denying login for UUID '{username}': Maximum server count of {max_server_count} reached. Consider deleting some servers.")
    sys.exit(3)

logger.info(f"Creating or updating Server object for UUID: {username}")

server, created = Server.objects.update_or_create(
    uuid=username,
    defaults={
        "uuid": username,
        "fqdn": password,
    }
)

logger.info(f"Authentication successful for Server with UUID: {username}")
