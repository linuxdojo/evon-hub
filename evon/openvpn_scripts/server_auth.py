#!/opt/evon-hub/.env/bin/python

##############################################
# Evon OpenVPN Server Non-blocking Auth Script
##############################################

# This script uses https://github.com/mozilla-it/openvpn_defer_auth for asunc auth


import os
import sys
import pwd

if os.getuid() and pwd.getpwuid(os.getuid())[0] == "openvpn":
    os.execl(
        "/usr/bin/sudo",
        "-i",
        sys.argv[0],
        os.environ["username"],
        os.environ["password"],
        os.environ["auth_control_file"]
    )

import evon  # noqa
import django
os.environ['DJANGO_SETTINGS_MODULE'] = 'eapi.settings'
django.setup()
from hub.models import Server, Config, vpn_ipv4_addresses  # noqa
from evon.log import get_evon_logger  # noqa


# Setup vars
logger = get_evon_logger()
username = os.environ.get("username") or sys.argv[1]
password = os.environ.get("password") or sys.argv[2]
auth_control_file = os.environ.get("auth_control_file") or sys.argv[3]
config = Config.get_solo()


def respond_with(auth_result, rc=0, control_path=auth_control_file):
    """
    Passes auth result to openvpn via control file and return code.
    `auth_result` is bool, True for success
    """
    import subprocess
    result_char = "1" if auth_result else "0"
    subprocess.run(
        [
            'sudo', '-u', 'openvpn', 'sh', '-c',
            f'echo "{result_char}" > {control_path}'
        ],
        check=True
    )
    sys.exit(0 if auth_result else (1 if rc == 0 else rc))


logger.info(f"Authenticating (using non-blocking) new Server connection with UUID: {username}")

if username in config.uuid_blacklist.split(","):
    logger.warning(f"Denying login for UUID '{username}': UUID is blacklisted in Hub Config.")
    respond_with(False, rc=1)

if not config.discovery_mode:
    # if uuid is not associated with a current server, and username is not whitelisted
    if not Server.objects.filter(uuid=username).first() and username not in config.uuid_whitelist.split(","):
        logger.warning(f"Denying login for UUID '{username}': discovery_mode is disabled and UUID is not known nor whitelisted.")
        respond_with(False, rc=2)

server_count = Server.objects.count()
max_server_count = len(vpn_ipv4_addresses())
if server_count == max_server_count:
    logger.error(f"Denying login for UUID '{username}': Maximum server count of {max_server_count} reached. Consider deleting some servers.")
    respond_with(False, rc=3)

logger.info(f"Creating or updating Server object for UUID: {username}")

server, created = Server.objects.update_or_create(
    uuid=username,
    defaults={
        "uuid": username,
        "fqdn": password,
    }
)

logger.info(f"Authentication successful for Server with UUID: {username}")
respond_with(True)
