#!/usr/bin/env python

import logging
import logging.handlers

import requests


# setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)
syslog_handler = logging.handlers.SysLogHandler(address = '/dev/log')
stdout_handler = logging.StreamHandler(sys.stdout)
fmt = logging.Formatter(fmt='evon[%(process)d]: %(levelname)s: %(message)s')
syslog_handler.setFormatter(fmt)
stdout_handler.setFormatter(fmt)
logger.addHandler(syslog_handler)

