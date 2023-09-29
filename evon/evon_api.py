
#################################
# EVON API Client
#################################

import base64
import json
import logging
import os
import subprocess

import requests

from eapi.settings import EVON_VARS
from evon import log


logger = log.get_evon_logger()
EVON_DEBUG = os.environ.get('EVON_DEBUG', '').upper() == "TRUE"
if EVON_DEBUG:
    logger.setLevel(logging.DEBUG)
# API_URL = os.environ.get("EVON_API_URL")
REQUESTS_TIMEOUT = 30
STANDALONE_MODE = EVON_VARS["standalone"]
STANDALONE_HOOK_PATH = EVON_VARS["standalone_hook_path"]


def generate_headers(api_key):
    response = requests.get(
        "http://169.254.169.254/latest/dynamic/instance-identity/document",
        timeout=REQUESTS_TIMEOUT
    )
    iid = base64.b64encode(response.text.encode("utf-8"))
    response = requests.get(
        "http://169.254.169.254/latest/dynamic/instance-identity/signature",
        timeout=REQUESTS_TIMEOUT
    )
    iid_signature = response.text.replace("\n", "")
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": api_key,
        "document": iid,
        "signature": iid_signature
    }
    logger.debug(f"headers are: {headers}")
    return headers


def get_pub_ipv4():
    response = requests.get(
        "http://169.254.169.254/latest/meta-data/public-ipv4",
        timeout=REQUESTS_TIMEOUT
    )
    return response.text


def do_request(url, requests_method, headers, json_payload=None, params={}):
    if STANDALONE_MODE:
        logger.info(f"standalone mode enabled, calling standalone hook at path: {STANDALONE_HOOK_PATH}")
        env = {
            **os.environ,
            "EVON_HOOK_REQUEST_URL": url,
            "EVON_HOOK_REQUEST_METHOD": requests_method.__name__,
            "EVON_HOOK_HEADERS": json.dumps(headers),
            "EVON_HOOK_BODY": json_payload or "",
            "EVON_HOOK_PARAMS": json.dumps(params),
        }
        p = subprocess.Popen(STANDALONE_HOOK_PATH, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, close_fds=True)
        rc = p.wait()
        stdout = p.stdout
        stderr = p.stderr
        stdout = stdout and stdout.read().decode() or ""
        stderr = stderr and stderr.read().decode() or ""
        logger.info(f"results after executing standalone hook: rc: {rc}, stdout: {stdout}, stderr: {stderr}")
    else:
        request_kwargs = {
            "headers": headers,
        }
        if json_payload:
            request_kwargs["data"] = json_payload.encode("utf-8")
        if params:
            request_kwargs["params"] = params
        response = None
        try:
            response = requests_method(url, **request_kwargs, timeout=REQUESTS_TIMEOUT)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            logger.error(f"{requests_method.__name__.upper()} request failed: '{e}' ")
        return response


def get_records(api_url, api_key):
    url = f"{api_url}/zone/records"
    response = do_request(
        url,
        requests.get,
        headers=generate_headers(api_key)
    )
    records = json.dumps(json.loads(response.text), indent=2)
    return records


def set_records(api_url, api_key, json_payload, usage_stats=False):
    url = f"{api_url}/zone/records"
    if usage_stats:
        url += "?usage_stats=true"
    response = do_request(
        url,
        requests.put,
        headers=generate_headers(api_key),
        json_payload=json_payload
    )
    return response.text


def register(api_url, api_key, json_payload):
    url = f"{api_url}/zone/register"
    response = do_request(
        url,
        requests.post,
        headers=generate_headers(api_key),
        json_payload=json_payload
    )
    return response.text


def deregister(api_url, api_key, json_payload):
    url = f"{api_url}/zone/deregister"
    response = do_request(
        url,
        requests.delete,
        headers=generate_headers(api_key),
        json_payload=json_payload
    )
    return response.text


def get_updates(api_url, api_key, version, selfhosted=False):
    url = f"{api_url}/zone/update/{version}"
    response = do_request(
        url,
        requests.get,
        headers=generate_headers(api_key),
        params={"selfhosted": selfhosted}
    )
    return response.text


def get_meters(api_url, api_key):
    url = f"{api_url}/zone/meters"
    response = do_request(
        url,
        requests.get,
        headers=generate_headers(api_key)
    )
    return response.text


def get_usage_limits(api_url, api_key):
    url = f"{api_url}/zone/meters?usage_limits=true"
    response = do_request(
        url,
        requests.get,
        headers=generate_headers(api_key)
    )
    return response.text
