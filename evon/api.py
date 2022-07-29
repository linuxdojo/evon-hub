
#################################
# EVON API Client
#################################

import base64
import os

import requests

from evon import log


logger = log.get_evon_logger()
EVON_DEBUG = os.environ.get('EVON_DEBUG', '').upper() == "TRUE"
if EVON_DEBUG:
    logger.setLevel(logging.DEBUG)
API_KEY = os.environ.get("EVON_API_KEY")
API_URL = os.environ.get("EVON_API_URL", "https://dev.api.evon.link")


def generate_headers():
    response = requests.get("http://169.254.169.254/latest/dynamic/instance-identity/document")
    iid = base64.b64encode(response.text.encode("utf-8"))
    response = requests.get("http://169.254.169.254/latest/dynamic/instance-identity/signature")
    iid_signature = response.text
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY,
        "document": iid,
        "signature": iid_signature
    }
    return headers


def get_pub_ipv4():
    response = requests.get("http://169.254.169.254/latest/meta-data/public-ipv4")
    return response.text


def get_records():
    url = f"{API_URL}/zone/records"
    try:
        response = requests.GET(headers=generate_headers())
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        logger.error(f"Got error response from GET {url}: {err}")
            raise err
    return response.text


def set_records(changes):
    url = f"{API_URL}/zone/records"
    try:
        response = requests.PUT(
            headers=generate_headers(),
            body=changes
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        logger.error(f"Got error response from PUT {url}: {err}")
            raise err
    return response.text

