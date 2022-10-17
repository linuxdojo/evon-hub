import os
import json

import django
os.environ['DJANGO_SETTINGS_MODULE'] = 'eapi.settings'  # noqa
django.setup()  # noqa
from django.contrib.auth.models import User  # noqa

from eapi.settings import EVON_HUB_CONFIG  # noqa
from hub.models import Server  # noqa
from evon import evon_api  # noqa
from evon.cli import EVON_API_URL, EVON_API_KEY, inject_pub_ipv4  # noqa
from evon.log import get_evon_logger  # noqa


logger = get_evon_logger()


def kill_server(uuid):
    vpn = EVON_HUB_CONFIG["vpn_mgmt_servers"]
    vpn.connect()
    uuids = [v.common_name for _, v in vpn.get_status().routing_table.items()]
    if uuid in uuids:
        result = vpn.send_command(f"kill {uuid}")
    else:
        result = "not connected"
    vpn.disconnect()
    logger.info(f"{result}")


def do_sync():
    """
    Sync all Server objects to reflect current connected state
    """
    # obtain current state
    all_servers = Server.objects.all()
    vpn = EVON_HUB_CONFIG["vpn_mgmt_servers"]
    vpn.connect()
    vpn_clients = {k: v.common_name for k, v in vpn.get_status().routing_table.items()}
    vpn.disconnect()

    # refresh django db
    connected_uuids = vpn_clients.values()
    for server in all_servers:
        if server.uuid in connected_uuids:
            if not server.connected:
                logger.info(f"toggling connected to True for server {server.fqdn}")
                server.connected = True
                server.save()
            else:
                logger.debug(f"leaving connected as True for server {server.fqdn}")
        else:
            if server.connected:
                logger.info(f"toggling connected to False for server {server.fqdn}")
                server.connected = False
                server.save()
            else:
                logger.debug(f"leaving connected as False for server {server.fqdn}")

    # refresh dns
    current_records = {k[:k.rfind(".")]: v for k, v in json.loads(evon_api.get_records(EVON_API_URL, EVON_API_KEY)).items()}
    current_clients = {Server.objects.get(ipv4_address=ip_addr).fqdn: ip_addr for ip_addr in vpn_clients.keys()}
    new = {}
    removed = {}
    updated = {}
    unchanged = {}
    for fqdn in current_records:
        if fqdn not in current_clients:
            removed[fqdn] = current_records[fqdn]
        elif current_clients[fqdn] == current_records[fqdn]:
            unchanged[fqdn] = current_records[fqdn]
        else:
            updated[fqdn] = current_clients[fqdn]
    for fqdn in current_clients:
        if fqdn not in current_records:
            new[fqdn] = current_clients[fqdn]
    payload = {
        "changes": {
            "new": new,
            "removed": removed,
            "updated": updated,
            "unchanged": unchanged
        }
    }
    logger.info(f"Applying DNS changes: {payload}")
    payload = inject_pub_ipv4(json.dumps(payload))
    response = evon_api.set_records(EVON_API_URL, EVON_API_KEY, payload)
    logger.info(f"set_records reponse: {response}")
