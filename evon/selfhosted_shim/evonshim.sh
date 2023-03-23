#!/bin/bash

if [ "$1" == "start" ]; then
    /usr/sbin/ip addr add 169.254.169.254/32 dev lo >/dev/null 2>&1 || :
    exec /opt/evon-hub/.env/bin/uvicorn \
        evon.selfhosted_shim.server:app \
        --host 169.254.169.254 \
        --port 80
elif [ "$1" == "stop" ]; then
    /usr/sbin/ip addr del 169.254.169.254/32 dev lo >/dev/null 2>&1 || :
    /bin/kill -s TERM $2
fi
