
#################################
# EVON API Client
#################################

import base64
import json
import logging
import os
import subprocess

from dotenv import dotenv_values
import requests

from evon import log


logger = log.get_evon_logger()
EVON_DEBUG = os.environ.get('EVON_DEBUG', '').upper() == "TRUE"
if EVON_DEBUG:
    logger.setLevel(logging.DEBUG)
# API_URL = os.environ.get("EVON_API_URL")
REQUESTS_TIMEOUT = 30
evon_env = dotenv_values(os.path.join(os.path.dirname(__file__), ".evon_env"))
STANDALONE_MODE = evon_env["STANDALONE"] == "True"
STANDALONE_HOOK_PATH = evon_env["STANDALONE_HOOK_PATH"]


class BytesEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, bytes):
            return obj.decode("utf-8")
        return json.JSONEncoder.default(self, obj)


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
            "EVON_HOOK_HEADERS": json.dumps(headers, cls=BytesEncoder),
            "EVON_HOOK_BODY": json_payload or "",
            "EVON_HOOK_PARAMS": json.dumps(params),
        }
        p = subprocess.Popen(STANDALONE_HOOK_PATH, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, close_fds=True, encoding="utf-8")
        rc = p.wait()
        stdout = p.stdout.read() or ""
        stderr = p.stderr.read() or ""
        logger.info(f"results after executing standalone hook: rc: {rc}, stdout: {stdout}, stderr: {stderr}")
        return stdout
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
        return response.text


def get_records(api_url, api_key):
    url = f"{api_url}/zone/records"
    response = do_request(
        url,
        requests.get,
        headers=generate_headers(api_key)
    )
    records = json.dumps(json.loads(response), indent=2)
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
    return response


def register(api_url, api_key, json_payload):
    url = f"{api_url}/zone/register"
    response = do_request(
        url,
        requests.post,
        headers=generate_headers(api_key),
        json_payload=json_payload
    )
    return response


def deregister(api_url, api_key, json_payload):
    url = f"{api_url}/zone/deregister"
    response = do_request(
        url,
        requests.delete,
        headers=generate_headers(api_key),
        json_payload=json_payload
    )
    return response


def get_updates(api_url, api_key, version, selfhosted=False):
    url = f"{api_url}/zone/update/{version}"
    response = do_request(
        url,
        requests.get,
        headers=generate_headers(api_key),
        params={"selfhosted": selfhosted}
    )
    return response


def get_meters(api_url, api_key):
    url = f"{api_url}/zone/meters"
    response = do_request(
        url,
        requests.get,
        headers=generate_headers(api_key)
    )
    return response


def get_usage_limits(api_url, api_key):
    url = f"{api_url}/zone/meters?usage_limits=true"
    response = do_request(
        url,
        requests.get,
        headers=generate_headers(api_key)
    )
    return response
