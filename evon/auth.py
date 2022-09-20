#!/opt/evon-hub/.env/bin/python

############################
# Evon OpenVPN Auth Script
############################


import os
import sys

import requests

import django
os.environ['DJANGO_SETTINGS_MODULE'] = 'eapi.settings'
django.setup()
from hub.models import UUID_PATTERN, Server, Config  # noqa
from log import get_evon_logger  # noqa


logger = get_evon_logger()

exit_codes = {
    "bad_uuidv4_pattern": 1,
    "discovery_disabled": 2,
    "bad_password": 3,
}
username = os.environ["username"]
password = os.environ["password"]
config = Config.get_solo()
ec2_id = requests.get("http://169.254.169.254/latest/dynamic/instance-identity/document").json()["instanceId"]

logger.info(f"validating new Server connection with username: {username}")

if not UUID_PATTERN.match(username):
    logger.warning(f"Denying login for user '{username}': Username is not a valid UUIDv4 string")
    sys.exit(exit_codes["bad_uuidv4_pattern"])

if password != ec2_id:
    logger.warning(f"Denying login for user '{username}': Password does not contain Hub EC2 instanceId")
    sys.exit(exit_codes["bad_password"])

if not config.discovery_mode and not Server.objects.filter(uuid=username).first():
    logger.warning(f"Denying login for user '{username}': discovery_mode disabled, not accepting new Servers")
    sys.exit(exit_codes["discovery_disabled"])

logger.info(f"Accepting connection for username: {username}")
