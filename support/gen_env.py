#!/usr/bin/env python

"""
Generates file `evon/.evon_env` containing env respective Evon Cloud API URL and Key as part of packaging.
"""

import os
import sys


ENV = os.environ.get("ENV")
HOSTED_MODE = os.environ.get("HOSTED_MODE", "").lower()


def validate_hosted_mode(hosted_mode):
    allowed_modes = ["awsmp", "selfhosted", "standalone"]
    if hosted_mode not in allowed_modes:
        print(f"ERROR: HOSTED_MODE env var must be one of: {', '.join(allowed_modes)}")
        sys.exit(1)


def get_api_key(env):
    if HOSTED_MODE == "standalone":
        return ""
    elif HOSTED_MODE = "selfhosted":
        api_key_name = f"evon-{env}-api-selfhosted-apikey"
    else:
        api_key_name = f"evon-{env}-api-apikey"
    import boto3
    client = boto3.client('apigateway')
    resp = client.get_api_keys()
    key_id = [k for k in resp["items"] if k["name"] == api_key_name].pop()["id"]
    key = client.get_api_key(apiKey=key_id, includeValue=True)["value"]
    return key


def get_domain_suffix(env):
    if HOSTED_MODE == "standalone":
        return "__STANDALONE__"
    if env in ["dev", "staging"]:
        return f"{env}.evon.link"
    else:
        return "evon.link"


def get_api_url(env):
    if HOSTED_MODE == "standalone":
        return ""
    domain_suffix = get_domain_suffix(env)
    return f"https://api.{domain_suffix}"


def store_env(api_url, api_key, env):
    env_abs_path = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "evon", ".evon_env"))
    domain_suffix = get_domain_suffix(env)
    selfhosted = HOSTED_MODE in ["selfhosted", "standalone"]
    standalone = HOSTED_MODE == "standalone"
    content = (
        f'EVON_API_URL="{api_url}"\n'
        f'EVON_API_KEY="{api_key}"\n'
        f'EVON_ENV="{env}"\n'
        f'EVON_DOMAIN_SUFFIX="{domain_suffix}"\n'
        f'HOSTED_MODE="{HOSTED_MODE}"\n'
        f'SELFHOSTED="{selfhosted}"\n'
        f'STANDALONE="{standalone}"\n'
        'STANDALONE_HOOK_PATH="/opt/evon_standalone_hook"\n'
    )
    with open(env_abs_path, "w") as f:
        f.write(content)
    return env_abs_path


if __name__ == "__main__":
    api_url = get_api_url(ENV)
    api_key = get_api_key(ENV)
    res = store_env(api_url, api_key, ENV)
    print(f"Wrote: {res}")
