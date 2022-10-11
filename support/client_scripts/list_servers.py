#!/usr/bin/env python

import requests

url="https://xxxxx.evon.link/api/server"
auth_token="xxx"

print("IPv4           \t State\t FQDN")
while url != None:
    data = requests.get(url, headers={"Authorization": f"Token {auth_token}"}).json()
    for server in data['results']:
        state = "up" if server["connected"] else "down"
        print(f"{server['ipv4_address']} \t {state} \t {server['fqdn']}")
    url = data["next"]
