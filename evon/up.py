#!/opt/evon-hub/.env/bin/python

############################
# Evon OpenVPN Up Script
############################


import os
import sys

import json
import requests

import django
os.environ['DJANGO_SETTINGS_MODULE'] = 'eapi.settings'
django.setup()
from hub.models import Server  # noqa
from log import get_evon_logger  # noqa


logger = get_evon_logger()

logger.info(f"args: {sys.argv}")
logger.info(f"env: {json.dumps(dict(os.environ), indent=2)}")
