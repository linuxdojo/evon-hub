
#################################
# EVON Logger
#################################


import logging
import logging.handlers
import sys


def get_evon_logger():
    # setup logging
    logger = logging.getLogger()
    logger.handlers = []
    logger.setLevel(logging.INFO)
    syslog_handler = logging.handlers.SysLogHandler(address='/dev/log')
    stderr_handler = logging.StreamHandler(sys.stderr)
    syslog_fmt = logging.Formatter(fmt='evon[%(process)d]: %(levelname)s: %(message)s')
    stderr_fmt = logging.Formatter(fmt='%(asctime)s - %(levelname)s: %(message)s')
    syslog_handler.setFormatter(syslog_fmt)
    stderr_handler.setFormatter(stderr_fmt)
    logger.addHandler(syslog_handler)
    logger.addHandler(stderr_handler)
    return logger
