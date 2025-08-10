#!/opt/evon-hub/.env/bin/python

##################################
# Evon OpenVPN User Auth Script
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
from django.contrib.auth import authenticate  # noqa
from evon.log import get_evon_logger  # noqa


logger = get_evon_logger()
username = os.environ.get("username") or sys.argv[1]
password = os.environ.get("password") or sys.argv[2]

logger.info(f"Authenticating new User connection with username: {username}")

user = authenticate(username=username, password=password)
if not user:
    logger.error(f"Denying login for user '{username}': incorrect password")
    sys.exit(1)

logger.info(f"Authenticated User connection for username: {username}")
