#!/usr/bin/env python

"""
Generates file `evon/.evon_env` containing env respective api key/url as part of packaging.
"""

import os

import boto3


ENV = os.environ.get("ENV")
client = boto3.client('apigateway')


def get_api_key(env):
    api_key_name = f"evon-{env}-api-apikey"
    resp = client.get_api_keys()
    key_id = [k for k in resp["items"] if k["name"] == api_key_name].pop()["id"]
    key = client.get_api_key(apiKey=key_id, includeValue=True)["value"]
    return key


def get_api_url(env):
    if env in ["dev", "staging"]:
        return f"https://api.{env}.evon.link"
    return "https://api.evon.link"


def store_env(api_url, api_key):
    env_abs_path = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "evon", ".evon_env"))
    content = f'EVON_API_URL="{api_url}"\nEVON_API_KEY="{api_key}"'
    with open(env_abs_path, "w") as f:
        f.write(content)
    return env_abs_path


if __name__ == "__main__":
    api_url = get_api_url(ENV)
    api_key = get_api_key(ENV)
    res = store_env(api_url, api_key)
    print(f"Wrote: {res}")
