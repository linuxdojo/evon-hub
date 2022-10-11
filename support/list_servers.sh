#!/bin/bash

url="https://xxxxx.evon.link/api/server"
auth_token="xxx"

echo -e "IPv4           \t State\t FQDN"
while [ "${url}" != "null" ]; do
    response=$(curl -s "${url}" -H "Authorization: Token ${auth_token}")
    echo ${response} | \
        jq -rM '.results[] | .ipv4_address + " " + (.connected|tostring) + " " + .fqdn' | \
            sed 's/ /\t /g' | sed 's/true/up/g' | sed 's/false/down/g'
    url=$(echo $response | jq -r '.next')
done
