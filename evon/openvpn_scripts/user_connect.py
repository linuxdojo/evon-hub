#!/opt/evon-hub/.env/bin/python

#######################################
# Evon OpenVPN User Connect Script
#######################################


import os
import sys
import pwd

if os.getuid() and pwd.getpwuid(os.getuid())[0] == "openvpn":
    os.execl("/usr/bin/sudo", "-i", sys.argv[0], os.environ["common_name"], sys.argv[-1])

import ipaddress
import django
os.environ['DJANGO_SETTINGS_MODULE'] = 'eapi.settings'
django.setup()
from hub.models import User  # noqa
from evon.log import get_evon_logger  # noqa


logger = get_evon_logger()
if not len(sys.argv) >= 2:
    logger.error("Did not receive any args")
    sys.exit(1)
ccd_file = sys.argv[-1]
cn = os.environ.get("common_name") or sys.argv[1]

logger.info(f"Setting up CCD file for user with common name: {cn}")

if not os.access(ccd_file, os.W_OK):
    logger.error(f"Specified CCD file not writable: {ccd_file}")
    sys.exit(1)

if os.path.getsize(ccd_file):
    logger.error(f"Specified CCD file not empty: {ccd_file}")
    sys.exit(1)

user = User.objects.filter(username=cn).first()
if not user:
    logger.error(f"User with username '{cn}' does not exist")
    sys.exit(1)

# generate dynamic CCD content for client
local = user.userprofile.ipv4_address
remote = ipaddress.ip_address(local) - 1
ccd_config = f'ifconfig-push {local} {remote}'
#with open(ccd_file, "w") as f:
#    f.write(ccd_config)
# XXX above yields:
#   PermissionError: [Errno 13] Permission denied: '/tmp/openvpn_cc_2e4c9ed50581c7ed38138f28c8483f1e.tmp'
#   Workaround with os.system below.
os.system(f"echo {ccd_config} > {ccd_file}")

logger.info(f"Wrote CCD file '{ccd_file}' with content: {ccd_config}")
