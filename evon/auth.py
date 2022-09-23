#!/opt/evon-hub/.env/bin/python

############################
# Evon OpenVPN Auth Script
############################


import os
import sys

import django
os.environ['DJANGO_SETTINGS_MODULE'] = 'eapi.settings'
django.setup()
from hub.models import Server, Config  # noqa
from log import get_evon_logger  # noqa


logger = get_evon_logger()
username = os.environ["username"]
password = os.environ["password"]
config = Config.get_solo()


logger.info(f"validating new Server connection with username: {username}")

if not config.discovery_mode and not Server.objects.filter(uuid=username).first():
    logger.warning(f"Denying login for user '{username}': discovery_mode disabled, not accepting new Servers")
    sys.exit(1)

logger.info(f"Creating or updating Server object for UUID: {username}")

server, created = Server.objects.update_or_create(
    uuid=username,
    defaults={
        "uuid": username,
        "fqdn": password,
    }
)

logger.info(f"Accepting connection for username: {username}")
