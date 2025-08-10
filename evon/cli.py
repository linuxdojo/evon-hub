#!/usr/bin/env python
# flake8: noqa

#################################
# EVON CLI
#################################


from importlib.metadata import version
from rich.console import Console
import io
import json
import logging
import logging.handlers
import os
import subprocess
import stat
import sys
import textwrap

from dotenv import dotenv_values
import click
import requests
import yaml

from evon import log, evon_api

logger = log.get_evon_logger()
EVON_DEBUG = os.environ.get('EVON_DEBUG', '').upper() == "TRUE"
if EVON_DEBUG:
    logger.setLevel(logging.DEBUG)
EVON_VERSION = version('evon')
evon_env = dotenv_values(os.path.join(os.path.dirname(__file__), ".evon_env"))
EVON_API_KEY = evon_env["EVON_API_KEY"]
EVON_API_URL = evon_env["EVON_API_URL"]
EVON_DOMAIN_SUFFIX = evon_env["EVON_DOMAIN_SUFFIX"]
SELFHOSTED = evon_env["SELFHOSTED"].lower() == "true"
EVON_ENV = evon_env["EVON_ENV"]
MUTEX_OPTIONS = [
    "get_inventory",
    "set_inventory",
    "get_account_info",
    "register",
    "deregister",
    "get_deploy_key",
    "check_update",
    "update",
    "save_state",
    "sync_servers",
    "kill_server",
    "sync_pubip",
    "iam_validate",
    "mp_meter",
    "reset_admin_pw",
    "netstats",
    "get_usage_limits",
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
                    f"--{self.name.replace('_', '-')}",
                    ', '.join([f"--{a.replace('_', '-')}" for a in self.mutually_exclusive])
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
    current_public_ipv4 = evon_api.get_pub_ipv4()
    data["public-ipv4"] = current_public_ipv4
    # sync current pub ipv4 with saved ipv4 in evon_vars.yaml if changed
    evon_vars_path = os.path.join(os.path.dirname(__file__), "..", "evon_vars.yaml")
    if os.path.isfile(evon_vars_path):
        with open(evon_vars_path) as f:
            evon_vars = yaml.safe_load(f)
        saved_public_ipv4 = evon_vars["public_ipv4"]
        if current_public_ipv4 != saved_public_ipv4:
            logger.info(f"Detected public ipv4 addres change from {saved_public_ipv4} to {current_public_ipv4}. Persisting in evon_vars.yaml...")
            # update evon_vars.yaml
            evon_vars["public_ipv4"] = current_public_ipv4
            with open(evon_vars_path, "w") as f:
                f.write(f"---\n{yaml.dump(evon_vars)}")
    return json.dumps(data)


def get_account_info():
    """
    Sends a PUT to evon cloud api set_records function with empty changeset. This returns account info
    and has the side effect of updating Route53 with the curent public ipv4 of this ec2 instance.
    """
    logger.info("getting account info...")
    json_payload = '{"changes": {"new": {}, "removed": {}, "updated": {}, "unchanged": {}}}'
    json_payload = inject_pub_ipv4(json_payload)
    result = json.loads(evon_api.set_records(EVON_API_URL, EVON_API_KEY, json_payload))
    # append ec2 instance id
    response = requests.get("http://169.254.169.254/latest/dynamic/instance-identity/document")
    iid = response.json()["instanceId"]
    result["ec2_instance_id"] = iid
    return result


def sync_pub_ipv4():
    """
    Fucntion to check if saved ipv4 (in evon_vars.yaml) == current ipv4, and if not, fires the
    get_account_info() function which PUTs to evon cloud API and updates route53. 
    """
    result = {"pub_ipv4_changed": False}
    current_public_ipv4 = evon_api.get_pub_ipv4()
    evon_vars_path = os.path.join(os.path.dirname(__file__), "..", "evon_vars.yaml")
    if os.path.isfile(evon_vars_path):
        with open(evon_vars_path) as f:
            evon_vars = yaml.safe_load(f)
        saved_public_ipv4 = evon_vars["public_ipv4"]
        if current_public_ipv4 != saved_public_ipv4:
            logger.info(f"Detected public ipv4 addres change from {saved_public_ipv4} to {current_public_ipv4}. Updating DNS...")
            get_account_info()
            result["pub_ipv4_changed"] = True
    return result


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
    "--sync-pubip",
    "-p",
    cls=MutuallyExclusiveOption,
    mutually_exclusive=[o for o in MUTEX_OPTIONS if o != "sync_pubip"],
    is_flag=True,
    help="Sync public DNS record for this Hub with current public ipv4 address"
)
@click.option(
    "--iam-validate",
    cls=MutuallyExclusiveOption,
    mutually_exclusive=[o for o in MUTEX_OPTIONS if o != "iam_validate"],
    is_flag=True,
    help="Validate IAM Role attached to this EC2"
)
@click.option(
    "--mp-meter",
    cls=MutuallyExclusiveOption,
    mutually_exclusive=[o for o in MUTEX_OPTIONS if o != "mp_meter"],
    is_flag=True,
    hidden=True,
    help="Send metering records to AWS"
)
@click.option(
    "--get-inventory",
    "-i",
    cls=MutuallyExclusiveOption,
    mutually_exclusive=[o for o in MUTEX_OPTIONS if o != "get_inventory"],
    is_flag=True,
    help="Show inventory of all zone records (registered public A records) for Servers that are currently connected to the Hub."
)
@click.option(
    "--set-inventory",
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
    help="Get registered account info."
)
@click.option(
    "--register",
    "-r",
    cls=MutuallyExclusiveOption,
    mutually_exclusive=[o for o in MUTEX_OPTIONS if o != "register"],
    metavar="JSON",
    help="Register new account. Specify JSON in the following format: "
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
         "OpenVPN config to be uninstalled or reinstalled if subsequent re-registration "
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
    "--check-update",
    "-c",
    cls=MutuallyExclusiveOption,
    mutually_exclusive=[o for o in MUTEX_OPTIONS if o != "check_update"],
    is_flag=True,
    help="Check if an Evon Hub update is available"
)
@click.option(
    "--update",
    "-u",
    cls=MutuallyExclusiveOption,
    mutually_exclusive=[o for o in MUTEX_OPTIONS if o != "update"],
    is_flag=True,
    help="Apply the latest Evon Hub update if available. "
         "Note that the Evon Hub WebUI and API may become unavailable for a few minutes during the update process, "
         "however Servers and Users connected to the Hub will not be affected and will be "
         "able to communicate as normal throughout the update process."
)
@click.option(
    "--save-state",
    cls=MutuallyExclusiveOption,
    mutually_exclusive=[o for o in MUTEX_OPTIONS if o != "save_state"],
    is_flag=True,
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
    "--reset-admin-pw",
    cls=MutuallyExclusiveOption,
    mutually_exclusive=[o for o in MUTEX_OPTIONS if o != "reset_admin_pw"],
    is_flag=True,
    help="Reset the Admin password"
)
@click.option(
    "--netstats",
    cls=MutuallyExclusiveOption,
    mutually_exclusive=[o for o in MUTEX_OPTIONS if o != "netstats"],
    is_flag=True,
    help="Calculate and register netstats"
)
@click.option(
    "--get-usage-limits",
    cls=MutuallyExclusiveOption,
    mutually_exclusive=[o for o in MUTEX_OPTIONS if o != "get_usage_limits"],
    is_flag=True,
    help="Retrieve usage limits for this Hub instance"
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
        click.echo(json.dumps({"version": f"{EVON_VERSION}"}, indent=2))

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
        result = get_account_info()
        click.echo(json.dumps(result, indent=2))

    if kwargs["sync_pubip"]:
        logger.info("syncing public ipv4 with hub's route53 A record if changed...")
        result = sync_pub_ipv4()
        click.echo(json.dumps(result, indent=2))

    if kwargs["check_update"]:
        logger.info("Checking for updates...")
        result = json.loads(evon_api.get_updates(EVON_API_URL, EVON_API_KEY, EVON_VERSION, selfhosted=SELFHOSTED))
        result["status"] = "success"
        click.echo(json.dumps(result, indent=2))

    if kwargs["update"]:
        evon_vars_path = os.path.join(os.path.dirname(__file__), "..", "evon_vars.yaml")
        if not os.path.isfile(evon_vars_path):
            logger.error("ERROR: Evon Hub not yet deployed. Run 'evon-deploy' first.")
            sys.exit(1)
        with open(evon_vars_path) as f:
            evon_vars = yaml.safe_load(f)
        domain_prefix = evon_vars["account_domain"].split(".")[0]
        subnet_key = evon_vars["subnet_key"]
        logger.info("Checking for updates...")
        result = json.loads(evon_api.get_updates(EVON_API_URL, EVON_API_KEY, EVON_VERSION, selfhosted=SELFHOSTED))
        if result["update_available"]:
            # download and run update
            new_version = result["update_version"]
            logger.info(f"New Evon Hub version {new_version} available, downloading...")
            r = requests.get(result["presigned_url"])
            logger.info("Upgrading to new version...")
            if SELFHOSTED:
                installer_path = "/tmp/evon-deploy"
            else:
                installer_path = "/home/ec2-user/bin/evon-deploy"
            with open(installer_path, "wb") as f:
                f.write(r.content)
            os.chmod(installer_path, os.stat(installer_path).st_mode | stat.S_IEXEC) 
            cmd = f"{installer_path} --domain-prefix {domain_prefix} --subnet-key {subnet_key}"
            if SELFHOSTED:
                hwaddr = evon_vars["ec2_id"]
                cmd += f" --hwaddr {hwaddr}"
            p = subprocess.Popen(cmd, shell=True, close_fds=True, stdout=sys.stderr, stderr=sys.stderr)
            rc = p.wait()
            if rc:
                logger.error(f"Got non-zero return code {rc} from update process, see above for errors.")
                click.echo(json.dumps({"status": "failed", "message": f"error: rc {rc}"}, indent=2))
            else:
                logger.info(f"Update to version {new_version} complete.")
                click.echo(json.dumps({"status": "success", "message": "complete"}, indent=2))
        else:
            logger.info("No new updates are available.")
            click.echo(json.dumps({"status": "success", "message": "no updates available"}, indent=2))

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
        kwargs["debug"] and logger.setLevel(logging.DEBUG)  # set loglevel as import may clobber it
        logger.info("syncing server connected state...")
        try:
            sync_servers.do_sync()
            click.echo('{"status": "success"}')
        except Exception as e:
            click.echo(f'{{"status": "failed", "message": "{e}"}}')

    if kwargs["kill_server"]:
        from evon import sync_servers
        kwargs["debug"] and logger.setLevel(logging.DEBUG)  # set loglevel as import may clobber it
        uuid = kwargs["kill_server"]
        logger.info(f"Disconnecting server with uuid {uuid}:...")
        try:
            res = sync_servers.kill_server(uuid)
            click.echo(f'{{"status": "success", "message": "{res}"}}')
        except Exception as e:
            click.echo(f'{{"status": "failed", "message": "{e}"}}')

    if kwargs["iam_validate"]:
        from evon import sync_mp
        kwargs["debug"] and logger.setLevel(logging.DEBUG)  # set loglevel as import may clobber it
        logger.info("validating IAM Role attached to this EC2 instance...")
        try:
            response = sync_mp.validate_ec2_role(env=EVON_ENV)
            click.echo(json.dumps(response))
        except Exception as e:
            click.echo(f'{{"status": "failed", "message": "{e}"}}')
            sys.exit(2)

    if kwargs["mp_meter"]:
        if SELFHOSTED:
            logger.info("Selfhoted mode enabled, skipping registering meters with AWS metering API")
            click.echo(json.dumps({"message": "selfhosted mode enabled, skipping AWS metering registration"}))
            return
        from evon import sync_mp
        kwargs["debug"] and logger.setLevel(logging.DEBUG)  # set loglevel as import may clobber it
        logger.info("Registering meters with AWS metering API...")
        try:
            # register meters
            response = sync_mp.register_meters()
            # update last_meter_ts value in ddb record
            json_payload = '{"changes": {"new": {}, "removed": {}, "updated": {}, "unchanged": {}}, "last_meter_ts": "%s"}' % response["meter_timestamp"]
            json_payload = inject_pub_ipv4(json_payload)
            evon_api.set_records(EVON_API_URL, EVON_API_KEY, json_payload)
            click.echo(json.dumps(response))
        except Exception as e:
            click.echo(f'{{"status": "failed", "message": "{e}"}}')

    if kwargs["reset_admin_pw"]:
        logger.info("Resetting Admin password...")
        os.execl("/usr/local/bin/eapi", "/usr/local/bin/eapi", "changepassword", "admin")

    if kwargs["netstats"]:
        if not SELFHOSTED:
            logger.info("This option is for selfhosted mode systems only")
            click.echo(json.dumps({"message": "selfhosted mode disabled, skipping netstats registration"}))
            return
        from evon import netstats
        kwargs["debug"] and logger.setLevel(logging.DEBUG)  # set loglevel as import may clobber it
        logger.info("Calculating and registering netstats...")
        try:
            # register meters
            json_payload = json.dumps(netstats.main())
            json_payload = inject_pub_ipv4(json_payload)
            logger.debug(f"sending payload: {json_payload}")
            response = evon_api.set_records(EVON_API_URL, EVON_API_KEY, json_payload, usage_stats=True)
            click.echo(json.dumps(response))
        except Exception as e:
            click.echo(f'{{"status": "failed", "message": "{e}"}}')

    if kwargs["get_usage_limits"]:
        if not SELFHOSTED:
            logger.info("This option is for selfhosted mode systems only")
            click.echo(json.dumps({"message": "selfhosted mode disabled, skipping usage limits retrieval"}))
            return
        usage_limits = evon_api.get_usage_limits(EVON_API_URL, EVON_API_KEY)
        click.echo(usage_limits)
