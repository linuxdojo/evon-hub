#!/usr/bin/env python

#################################
# EVON CLI
#################################


import json
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


def get_inventory():
    response = api.get_records(EVON_API_URL, EVON_API_KEY)
    formatted_inventory = json.dumps(json.loads(response), indent=2)
    return formatted_inventory


@click.command()
@click.option(
    "--get-inventory",
    cls=log.MutuallyExclusiveOption,
    mutually_exclusive=["set_inventory"],
    is_flag=True, help="show inventory"
)
@click.option(
    "--set-inventory",
    cls=log.MutuallyExclusiveOption,
    mutually_exclusive=["get_inventory"],
    metavar="JSON",
    help=("Upsert/delete zone records specified as JSON in the following format: "
          """'{"upsert": {"fqdn": "ipv4", ...}, "delete": {"fqdn": "ipv4", ...}}'"""
    )
)
@click.option("--silent", is_flag=True, help="suppress all logs on stderr (logs will still be written to syslog)")
@click.option("--debug", is_flag=True, help="enable debug logging")
def main(**kwargs):
    """
    Evon Hub CLI. All logs are written to syslog, and will be printed to stderr unless --silent is specified.
    """
    if kwargs["debug"]:
        logger.setLevel(logging.DEBUG)
    if kwargs["silent"]:
        logger.handlers = [h for h in logger.handlers if "StreamHandler" not in h.__repr__()]
    logger.info(f"Evon client v{EVON_VERSION} starting - {sys.version}")

    if kwargs["get_inventory"]:
        logger.info("fetching inventory...")
        inventory = get_inventory()
        click.echo(inventory)

