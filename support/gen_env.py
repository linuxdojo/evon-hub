#!/usr/bin/env python

"""
Generates file `evon/.evon_env` containing env respective Evon Cloud API URL and Key as part of packaging.
"""

import os

import boto3


ENV = os.environ.get("ENV")
client = boto3.client('apigateway')


def get_api_key(env):
    if env == "selfhosted":
        return "null"
    api_key_name = f"evon-{env}-api-apikey"
    resp = client.get_api_keys()
    key_id = [k for k in resp["items"] if k["name"] == api_key_name].pop()["id"]
    key = client.get_api_key(apiKey=key_id, includeValue=True)["value"]
    return key


def get_domain_suffix(env):
    if env in ["dev", "staging"]:
        return f"{env}.evon.link"
    elif env == "selfhosted":
        return "__SELFHOSTED__"
    else:
        return "evon.link"


def get_api_url(env):
    if env == "selfhosted":
        return "http://127.0.0.1"
    domain_suffix = get_domain_suffix(env)
    return f"https://api.{domain_suffix}"


def store_env(api_url, api_key, env):
    env_abs_path = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "evon", ".evon_env"))
    domain_suffix = get_domain_suffix(env)
    content = f'EVON_API_URL="{api_url}"\nEVON_API_KEY="{api_key}"\nEVON_ENV="{env}"\nEVON_DOMAIN_SUFFIX="{domain_suffix}"'
    with open(env_abs_path, "w") as f:
        f.write(content)
    return env_abs_path


if __name__ == "__main__":
    api_url = get_api_url(ENV)
    api_key = get_api_key(ENV)
    res = store_env(api_url, api_key, ENV)
    print(f"Wrote: {res}")
