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

from evon import mapper


# setup logging
logger = logging.getLogger()
logger.handlers = []
logger.setLevel(logging.INFO)
syslog_handler = logging.handlers.SysLogHandler(address = '/dev/log')
stdout_handler = logging.StreamHandler(sys.stdout)
syslog_fmt = logging.Formatter(fmt='evon[%(process)d]: %(levelname)s: %(message)s')
stdout_fmt = logging.Formatter(fmt='%(asctime)s - %(levelname)s: %(message)s')
syslog_handler.setFormatter(syslog_fmt)
stdout_handler.setFormatter(stdout_fmt)
logger.addHandler(syslog_handler)
logger.addHandler(stdout_handler)

EVON_DEBUG = os.environ.get('EVON_DEBUG', '').upper() == "TRUE"
if EVON_DEBUG:
    logger.setLevel(logging.DEBUG)
EVON_VERSION = pkg_resources.require('evon')[0].version


def main():
    logger.info(f"Evon client v{EVON_VERSION} starting - {sys.version}")


if __name__ == "__main__":
    main()
