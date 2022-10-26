#!/usr/bin/env python
# flake8: noqa

#################################
# EVON CLI
#################################


import io
import json
import logging
import logging.handlers
import os
import pkg_resources
from rich.console import Console
import subprocess
import sys
import textwrap

import click
from dotenv import dotenv_values
import requests

from evon import log, evon_api

logger = log.get_evon_logger()
EVON_DEBUG = os.environ.get('EVON_DEBUG', '').upper() == "TRUE"
if EVON_DEBUG:
    logger.setLevel(logging.DEBUG)
EVON_VERSION = pkg_resources.require('evon')[0].version
evon_env = dotenv_values(os.path.join(os.path.dirname(__file__), ".evon_env"))
EVON_API_KEY = evon_env["EVON_API_KEY"]
EVON_API_URL = evon_env["EVON_API_URL"]
EVON_DOMAIN_SUFFIX = evon_env["EVON_DOMAIN_SUFFIX"]
MUTEX_OPTIONS = [
    "get_inventory",
    "get_account_info",
    "get_inventory",
    "save_state",
    "sync_servers",
]


class MutuallyExclusiveOption(click.Option):
    """
    Mutex group for Click. Example usage:
        @click.option("--silent", cls=MutuallyExclusiveOption, mutually_exclusive=["verbose"], is_flag=True, help="be silent")
        @click.option("--verbose", cls=MutuallyExclusiveOption, mutually_exclusive=["silent"], is_flag=True, help="be noisy")
    """

    def __init__(self, *args, **kwargs):
        self.mutually_exclusive = set(kwargs.pop('mutually_exclusive', []))
#        help = kwargs.get('help', '')
#        if self.mutually_exclusive:
#            ex_str = ', '.join(self.mutually_exclusive)
#            kwargs['help'] = help + (
#                ' NOTE: This argument is mutually exclusive with '
#                ' arguments: [' + ex_str + '].'
#            )
        super(MutuallyExclusiveOption, self).__init__(*args, **kwargs)

    def handle_parse_result(self, ctx, opts, args):
        if self.mutually_exclusive.intersection(opts) and self.name in opts:
            raise click.UsageError(
                "Illegal usage: `{}` is mutually exclusive with "
                "arguments `{}`.".format(
                    self.name,
                    ', '.join(self.mutually_exclusive)
                )
            )

        return super(MutuallyExclusiveOption, self).handle_parse_result(
            ctx,
            opts,
            args
        )


class RichCommand(click.Command):

    def format_help_text(self, ctx, formatter):
        sio = io.StringIO()
        console = Console(file=sio, force_terminal=True)
        console.print(
            textwrap.dedent(
                f"""
                 [bold green]__| |  |    \ \  |
                 _|  \  | () |  \ | Hub CLI
                ___|  _/  ___/_| _| v{EVON_VERSION}
               [ Elastic Virtual Overlay Network ]"""
            ),
            highlight=False,
        )
        formatter.write(sio.getvalue())


def inject_pub_ipv4(json_data):
    try:
        data = json.loads(json_data)
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON input: {e}")
        sys.exit(1)
    data["public-ipv4"] = evon_api.get_pub_ipv4()
    return json.dumps(data)


@click.command(
    cls=RichCommand,
    context_settings={
        "help_option_names": [
            '-h', '--help'
        ]
    },
    no_args_is_help=True,
)
@click.option(
    "--get-inventory",
    "-i",
    cls=MutuallyExclusiveOption,
    mutually_exclusive=[o for o in MUTEX_OPTIONS if o != "get_inventory"],
    is_flag=True, help="Show inventory."
)
@click.option(
    "--set-inventory",
    hidden=True,
    cls=MutuallyExclusiveOption,
    mutually_exclusive=[o for o in MUTEX_OPTIONS if o != "set_inventory"],
    metavar="JSON",
    help=("Upsert/delete zone records specified as JSON in the following format: "
          """'{"changes":{"new":{"fqdn":"ipv4",...},"removed":{"fqdn":"ipv4",...},"""
          """"updated":{"fqdn":"ipv4",...},"unchanged":{"fqdn":"ipv4",...}}}'"""
    )
)
@click.option(
    "--get-account-info",
    "-a",
    cls=MutuallyExclusiveOption,
    mutually_exclusive=[o for o in MUTEX_OPTIONS if o != "get_account_info"],
    is_flag=True,
    help="Get account info."
)
@click.option(
    "--register",
    "-r",
    cls=MutuallyExclusiveOption,
    mutually_exclusive=[o for o in MUTEX_OPTIONS if o != "register"],
    metavar="JSON",
    help="Register new account. Speficy JSON in the following format: "
          """'{"domain-prefix":"mycompany","subnet-key":"111"}'. """
          f'Your hub will be reachable at <domain-prefix>.{EVON_DOMAIN_SUFFIX}. '
          'Your overlay network subnet will be 100.<subnet-key>.224.0/19 where '
          '<subnet-key> is between 64 and 127 inclusive. Default is 111 if omitted.'
)
@click.option(
    "--deregister",
    "-x",
    cls=MutuallyExclusiveOption,
    mutually_exclusive=[o for o in MUTEX_OPTIONS if o != "deregister"],
    metavar="DOMAIN_PREFIX",
    help="Deregister account. You will be forced to interactively agree to "
         "the deregistration operation if invoked. Once an account is deregistered, "
         "all connected servers and user clients will need a new bootstrap.sh or "
         "OpenVPN config to be uninstalled or reinstalled if subsequent re-registration"
         "is performed."
)
@click.option(
    "--get-deploy-key",
    "-k",
    cls=MutuallyExclusiveOption,
    mutually_exclusive=[o for o in MUTEX_OPTIONS if o != "get_deploy_key"],
    is_flag=True,
    help="Get bootstrap deploy key."
)
@click.option(
    "--save-state",
    cls=MutuallyExclusiveOption,
    mutually_exclusive=[o for o in MUTEX_OPTIONS if o != "save_state"],
    is_flag=True,
    hidden=True,
    help="Deploy and persist state."
)
@click.option(
    "--sync-servers",
    cls=MutuallyExclusiveOption,
    mutually_exclusive=[o for o in MUTEX_OPTIONS if o != "sync_servers"],
    is_flag=True,
    help="Sync all Servers to reflect current connected state"
)
@click.option(
    "--kill-server",
    type=str,
    metavar="UUID",
    cls=MutuallyExclusiveOption,
    mutually_exclusive=[o for o in MUTEX_OPTIONS if o != "kill_server"],
    help="Disconnect server by UUID"
)
@click.option("--quiet", "-q", is_flag=True, help="Suppress all logs on stderr (logs will still be written to syslog at /var/log/evon.log).")
@click.option("--debug", "-d", is_flag=True, help="Enable debug logging.")
@click.option("--version", "-v", is_flag=True, help="Show version and exit.")
def main(**kwargs):
    """
    Evon CLI entrypoint
    """
    if kwargs["debug"]:
        logger.setLevel(logging.DEBUG)
    if kwargs["quiet"]:
        logger.handlers = [h for h in logger.handlers if "StreamHandler" not in h.__repr__()]

    logger.info(f"Evon client v{EVON_VERSION} starting - {sys.version}")

    if kwargs["version"]:
        click.echo(EVON_VERSION)
        sys.exit()

    if kwargs["get_inventory"]:
        logger.info("fetching inventory...")
        inventory = evon_api.get_records(EVON_API_URL, EVON_API_KEY)
        click.echo(inventory)

    if kwargs["set_inventory"]:
        logger.info("setting inventory...")
        json_payload = kwargs["set_inventory"]
        json_payload = inject_pub_ipv4(json_payload)
        logger.debug(f"updating inventory with payload: {json_payload}")
        result = evon_api.set_records(EVON_API_URL, EVON_API_KEY, json_payload)
        click.echo(result)

    if kwargs["register"]:
        logger.info("registering account...")
        json_payload = kwargs["register"]
        json_payload = inject_pub_ipv4(json_payload)
        result = json.loads(evon_api.register(EVON_API_URL, EVON_API_KEY, json_payload))
        # append ec2 instance id
        response = requests.get("http://169.254.169.254/latest/dynamic/instance-identity/document")
        iid = response.json()["instanceId"]
        result["ec2_instance_id"] = iid
        click.echo(json.dumps(result, indent=2))
        if not result.get("account_domain"):
            # didn't get expected response content, eg. profanity detected in requested domain-prefix. Exit with non-zero rc
            sys.exit(1)

    if kwargs["deregister"]:
        logger.info("deregistering account...")
        response = requests.get("http://169.254.169.254/latest/dynamic/instance-identity/document")
        iid = response.json()["instanceId"]
        answer = input(
            f'Are you sure you want to continue deregistring Evon account for this EC2 instance with ID {iid} (please type "yes" or "no")? '
        )
        if answer != "yes":
            click.echo("Aborting.")
            sys.exit()
        json_payload = json.dumps(
            {"domain-prefix": kwargs["deregister"]}
        )
        json_payload = inject_pub_ipv4(json_payload)
        result = json.loads(evon_api.deregister(EVON_API_URL, EVON_API_KEY, json_payload))
        # append ec2 instance id
        result["ec2_instance_id"] = iid
        click.echo(json.dumps(result, indent=2))

    if kwargs["get_account_info"]:
        logger.info("getting account info...")
        json_payload = '{"changes": {"new": {}, "removed": {}, "updated": {}, "unchanged": {}}}'
        json_payload = inject_pub_ipv4(json_payload)
        result = json.loads(evon_api.set_records(EVON_API_URL, EVON_API_KEY, json_payload))
        # append ec2 instance id
        response = requests.get("http://169.254.169.254/latest/dynamic/instance-identity/document")
        iid = response.json()["instanceId"]
        result["ec2_instance_id"] = iid
        click.echo(json.dumps(result, indent=2))

    if kwargs["get_deploy_key"]:
        logger.info("getting bootstrap deploy key...")
        import django
        os.environ['DJANGO_SETTINGS_MODULE'] = 'eapi.settings'
        django.setup()
        from django.contrib.auth.models import User
        deploy_key = User.objects.get(username="deployer").auth_token.key
        click.echo({"deploy_key": deploy_key})

    if kwargs["save_state"]:
        logger.info("deploying state...")
        p = subprocess.Popen(
            ". /opt/evon-hub/.env/bin/activate && cd /opt/evon-hub/ansible && make deploy",
            shell=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        while True:
            data = p.stdout.readline()
            if not data:
                break
            output = data.strip()
            output and logger.info(output)
        rc = p.wait()
        if not rc:
            click.echo('{"status": "success"}')
        else:
            click.echo(f'{{"status": "failed", "message": "Got non-zero return code: {rc}"}}')
            sys.exit(rc)

    if kwargs["sync_servers"]:
        from evon import sync_servers
        if kwargs["debug"]:
            logger.setLevel(logging.DEBUG)
        logger.info("syncing server connected state...")
        try:
            sync_servers.do_sync()
            click.echo('{"status": "success"}')
        except Exception as e:
            click.echo(f'{{"status": "failed", "message": "{e}"}}')

    if kwargs["kill_server"]:
        from evon import sync_servers
        if kwargs["debug"]:
            logger.setLevel(logging.DEBUG)
        uuid = kwargs["kill_server"]
        logger.info(f"Disconnecting server with uuid {uuid}:...")
        try:
            res = sync_servers.kill_server(uuid)
            click.echo(f'{{"status": "success", "message": "{res}"}}')
        except Exception as e:
            click.echo(f'{{"status": "failed", "message": "{e}"}}')
