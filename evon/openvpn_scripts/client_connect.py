#!/opt/evon-hub/.env/bin/python

#######################################
# Evon OpenVPN Client Connect Script
#######################################


import ipaddress
import os
import sys

import django
os.environ['DJANGO_SETTINGS_MODULE'] = 'eapi.settings'
django.setup()
from eapi.settings import EVON_VARS  # noqa
from hub.models import Server  # noqa
from evon.log import get_evon_logger  # noqa


logger = get_evon_logger()
if not len(sys.argv) >= 2:
    logger.error("Did not receive any args")
    sys.exit(1)
ccd_file = sys.argv[-1]
cn = os.environ["common_name"]

logger.info(f"Setting up CCD file for server with common name: {cn}")

if not os.access(ccd_file, os.W_OK):
    logger.error(f"Specified CCD file not writable: {ccd_file}")
    sys.exit(1)

if os.path.getsize(ccd_file):
    logger.error(f"Specified CCD file not empty: {ccd_file}")
    sys.exit(1)

server = Server.objects.filter(uuid=cn).first()
if not server:
    logger.error(f"Server with UUID '{cn}' does not exist")
    sys.exit(1)

# generate dynamic CCD content for client
local = server.ipv4_address
remote = ipaddress.ip_address(local) - 1
subnet_key = EVON_VARS["subnet_key"]
ccd_config = f'ifconfig-push {local} {remote}'
with open(ccd_file, "w") as f:
    f.write(ccd_config)

logger.info(f"Wrote CCD file '{ccd_file}' with content: {ccd_config}")

server.connected = True
server.save()
logger.info(f"set connected=True for {server.fqdn} with UUID {cn}")
