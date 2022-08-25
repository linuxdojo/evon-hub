#!/usr/bin/env python

import os


username = os.environ["username"]
password = os.environ["password"]

# TODO
# assert username is a UUID
# assert password is md5sum(UUID + ec2_id)
# assert username is not currently connected
# if mode == discovery
#   allow any username, create CCD entry if not present
#   if ip in pool, bounce connection
# elif mode == operational:
#    assert username present in CD
