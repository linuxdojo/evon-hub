#!/usr/bin/env python

import os
import re
import sys

import django
os.environ['DJANGO_SETTINGS_MODULE'] = 'eapi.settings'
django.setup()
from django.contrib.auth.models import User
from hub.models import UUID_PATTERN

from hub.log import get_evon_logger

username = os.environ["username"]
password = os.environ["password"]

logger = get_evon_logger()

if not UUID_PATTERN.match(username):
    logger.info(f"Denying login for user '{username}': Username is not a valid UUIDv4 string")
    sys.exit(1)
# assert username is a UUID
# assert password is md5sum(UUID + ec2_id)
# assert username is not currently connected
# if mode == discovery
#   allow any username, create CCD entry if not present
#   if ip in pool, bounce connection
# elif mode == operational:
#    assert username present in CD
