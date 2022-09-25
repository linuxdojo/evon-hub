import django
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'eapi.settings'  # noqa
django.setup()  # noqa
from django.contrib.auth.models import User  # noqa
import requests  # noqa

from eapi.settings import EVON_VARS  # noqa
from hub.models import Server  # noqa

from evon.log import get_evon_logger  # noqa


logger = get_evon_logger()


def do_sync():
    """
    Sync all Server objects to reflect current connected state
    """
    all_servers = Server.objects.all()
    api_key = User.objects.get(username="admin").auth_token
    api_url = EVON_VARS["account_domain"]
    headers = {"Authorization": f"Token {api_key}"}
    try:
        response = requests.get(
            f"https://{api_url}/api/openvpn/endpoints",
            headers=headers
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        logger.error(f"Got status {response.status_code} when querying state with exception: {e}")
        raise e
    openvpn_state = response.json()
    for server in all_servers:
        if server.uuid in openvpn_state.values():
            if not server.connected:
                logger.info(f"toggling connected to True for server {server.fqdn}")
                server.connected = True
                server.save()
            else:
                logger.info(f"leaving connected as True for server {server.fqdn}")
        else:
            if server.connected:
                logger.info(f"toggling connected to False for server {server.fqdn}")
                server.connected = False
                server.save()
            else:
                logger.info(f"leaving connected as False for server {server.fqdn}")
