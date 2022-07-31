#!/usr/bin/env python

#################################
# EVON CLI
#################################


import logging
import logging.handlers
import os
import pkg_resources
import sys

import click
import requests

from evon import log, api

logger = log.get_evon_logger()
EVON_DEBUG = os.environ.get('EVON_DEBUG', '').upper() == "TRUE"
if EVON_DEBUG:
    logger.setLevel(logging.DEBUG)
EVON_VERSION = pkg_resources.require('evon')[0].version
EVON_API_KEY = os.environ.get("EVON_API_KEY")
EVON_API_URL = os.environ.get("EVON_API_URL")


def register():
    ...


def get_inventory():
    response = api.get_records(EVON_API_URL, EVON_API_KEY)
    return response

@click.command()
@click.option("--get-inventory", is_flag=True, help="show inventory")
@click.option("--silent", is_flag=True, help="suppress all logs on stderr (logs will still be written to syslog)")
def main(**kwargs):
    """
    Evon Hub CLI
    """
    if kwargs["silent"]:
        logger.setLevel(logging.WARNING)
    logger.info(f"Evon client v{EVON_VERSION} starting - {sys.version}")

    if kwargs["get_inventory"]:
        click.echo(get_inventory())

