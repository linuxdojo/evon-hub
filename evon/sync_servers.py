import django
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'eapi.settings'  # noqa
django.setup()  # noqa
from django.contrib.auth.models import User  # noqa

from eapi.settings import EVON_HUB_CONFIG  # noqa
from hub.models import Server  # noqa

from evon.log import get_evon_logger  # noqa


logger = get_evon_logger()


def do_sync():
    """
    Sync all Server objects to reflect current connected state
    """
    all_servers = Server.objects.all()
    vpn = EVON_HUB_CONFIG["vpn_mgmt_servers"]
    vpn.connect()
    connected_uuids = [c.common_name for c in vpn.get_status().routing_table.values()]
    vpn.disconnect()
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
