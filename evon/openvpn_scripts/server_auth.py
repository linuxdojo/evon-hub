#!/opt/evon-hub/.env/bin/python

##################################
# Evon OpenVPN Server Auth Script
##################################


import os
import sys

import django
os.environ['DJANGO_SETTINGS_MODULE'] = 'eapi.settings'
django.setup()
from hub.models import Server, Config, vpn_ipv4_addresses  # noqa
from evon.log import get_evon_logger  # noqa


logger = get_evon_logger()
username = os.environ["username"]
password = os.environ["password"]
config = Config.get_solo()


logger.info(f"Authenticating new Server connection with username: {username}")

if not config.discovery_mode and not Server.objects.filter(uuid=username).first():
    logger.warning(f"Denying login for user '{username}': discovery_mode disabled, not accepting new Servers")
    sys.exit(1)

server_count = Server.objects.count()
max_server_count = len(vpn_ipv4_addresses())
if server_count == max_server_count:
    logger.error(f"Denying login for user '{username}': Maximum server count of {max_server_count} reached. Consider deleting some servers.")
    sys.exit(2)

logger.info(f"Creating or updating Server object for UUID: {username}")

server, created = Server.objects.update_or_create(
    uuid=username,
    defaults={
        "uuid": username,
        "fqdn": password,
    }
)

logger.info(f"Authenticated connection for username: {username}")
