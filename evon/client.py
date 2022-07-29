#!/usr/bin/env python

#################################
# EVON CLI
#################################


import logging
import logging.handlers
import os
import pkg_resources
import sys

import requests

from evon import log, api

logger = log.get_evon_logger()
EVON_DEBUG = os.environ.get('EVON_DEBUG', '').upper() == "TRUE"
if EVON_DEBUG:
    logger.setLevel(logging.DEBUG)
EVON_VERSION = pkg_resources.require('evon')[0].version


def main():
    logger.info(f"Evon client v{EVON_VERSION} starting - {sys.version}")


if __name__ == "__main__":
    main()
