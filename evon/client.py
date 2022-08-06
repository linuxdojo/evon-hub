#!/usr/bin/env python

#################################
# EVON CLI
#################################


import json
import logging
import logging.handlers
import os
import pkg_resources
import subprocess
import sys

import click
from dotenv import dotenv_values

from evon import log, api

logger = log.get_evon_logger()
EVON_DEBUG = os.environ.get('EVON_DEBUG', '').upper() == "TRUE"
if EVON_DEBUG:
    logger.setLevel(logging.DEBUG)
EVON_VERSION = pkg_resources.require('evon')[0].version
evon_env = dotenv_values(os.path.join(os.path.dirname(__file__), ".evon_env"))
EVON_API_KEY = evon_env["EVON_API_KEY"]
EVON_API_URL = evon_env["EVON_API_URL"]

MUTEX_OPTIONS = [
    "get_inventory",
    "get_account_info",
    "get_inventory",
    "save_state",
]

def inject_pub_ipv4(json_data):
    try:
        data = json.loads(json_data)
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON input: {e}")
        sys.exit(1)
    data["public-ipv4"] = api.get_pub_ipv4()
    return json.dumps(data)


@click.command(no_args_is_help=True)
@click.option(
    "--get-inventory",
    cls=log.MutuallyExclusiveOption,
    mutually_exclusive=[o for o in MUTEX_OPTIONS if o != "get_inventory"],
    is_flag=True, help="Show inventory."
)
@click.option(
    "--set-inventory",
    hidden=True,
    cls=log.MutuallyExclusiveOption,
    mutually_exclusive=[o for o in MUTEX_OPTIONS if o != "set_inventory"],
    metavar="JSON",
    help=("Upsert/delete zone records specified as JSON in the following format: "
          """'{"new": {"fqdn": "ipv4", ...},  "removed": {"fqdn": "ipv4", ...}, """
          """"updated": {"fqdn": "ipv4", ...}, "unchanged": {"fqdn": "ipv4", ...}}'"""
    )  # noqa
)
@click.option(
    "--get-account-info",
    cls=log.MutuallyExclusiveOption,
    mutually_exclusive=[o for o in MUTEX_OPTIONS if o != "get_account_info"],
    is_flag=True,
    help="Get account info."
)
@click.option(
    "--save-state",
    cls=log.MutuallyExclusiveOption,
    mutually_exclusive=[o for o in MUTEX_OPTIONS if o != "save_state"],
    is_flag=True,
    hidden=True,
    help="Deploy and persist state."
)
@click.option("--silent", is_flag=True, help="Suppress all logs on stderr (logs will still be written to syslog at /var/log/evon.log).")
@click.option("--debug", is_flag=True, help="Enable debug logging.")
@click.option("--version", is_flag=True, help="Show version and exit.")
def main(**kwargs):
    """
    Evon Hub CLI. 
    Output is written to stdout as JSON, logs are written to syslog and
    will also be echoed to stderr unless --silent is specified.
    """
    if kwargs["debug"]:
        logger.setLevel(logging.DEBUG)
    if kwargs["silent"]:
        logger.handlers = [h for h in logger.handlers if "StreamHandler" not in h.__repr__()]

    logger.info(f"Evon client v{EVON_VERSION} starting - {sys.version}")

    if kwargs["version"]:
        click.echo(EVON_VERSION)
        sys.exit()

    if kwargs["get_inventory"]:
        logger.info("fetching inventory...")
        inventory = api.get_records(EVON_API_URL, EVON_API_KEY)
        click.echo(inventory)

    if kwargs["set_inventory"]:
        logger.info("setting inventory...")
        json_payload = kwargs["set_inventory"]
        json_payload = inject_pub_ipv4(json_payload)
        logger.debug(f"updating inventory with payload: {json_payload}")
        result = api.set_records(EVON_API_URL, EVON_API_KEY, json_payload)
        click.echo(result)

    if kwargs["get_account_info"]:
        logger.info("getting account info...")
        json_payload = '{"changes": {"new": {}, "removed": {}, "updated": {}, "unchanged": {}}}'
        json_payload = inject_pub_ipv4(json_payload)
        result = api.set_records(EVON_API_URL, EVON_API_KEY, json_payload)
        click.echo(result)

    if kwargs["save_state"]:
        logger.info("deploying state...")
        try:
            subprocess.check_call(". /opt/evon-hub/.env/bin/activate && cd /opt/evon-hub/ansible && make deploy", shell=True, stdout=sys.stderr)
            click.echo('{"status": "success"}')
        except Exception as e:
            click.echo(f'{{"status": "failed", "message": "{e}"}}')
