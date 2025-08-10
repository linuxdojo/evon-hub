#!/opt/evon-hub/.env/bin/python

#########################################
# Evon OpenVPN Server Disconnect Script
#########################################


import os
import sys
import pwd

if os.getuid() and pwd.getpwuid(os.getuid())[0] == "openvpn":
    os.execl("/usr/bin/sudo", "-i", sys.argv[0], os.environ["common_name"])

import evon
import django
os.environ['DJANGO_SETTINGS_MODULE'] = 'eapi.settings'
django.setup()
from hub.models import Server  # noqa
from evon.log import get_evon_logger  # noqa


logger = get_evon_logger()
cn = os.environ.get("common_name") or sys.argv[1]

server = Server.objects.filter(uuid=cn).first()
if not server:
    logger.error(f"Server with UUID '{cn}' does not exist")
    sys.exit(1)

server.connected = False
server.save()
logger.info(f"set connected=False for {server.fqdn} with UUID {cn}")
