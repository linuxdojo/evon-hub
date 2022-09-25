#!/opt/evon-hub/.env/bin/python

#######################################
# Evon OpenVPN Client Disconnect Script
#######################################


import os
import sys

import django
os.environ['DJANGO_SETTINGS_MODULE'] = 'eapi.settings'
django.setup()
from hub.models import Server  # noqa
from evon.log import get_evon_logger  # noqa


logger = get_evon_logger()
cn = os.environ["common_name"]

server = Server.objects.filter(uuid=cn).first()
if not server:
    logger.error(f"Server with UUID '{cn}' does not exist")
    sys.exit(1)

server.connected = False
server.save()
logger.info(f"set connected=False for {server.fqdn} with UUID {cn}")
