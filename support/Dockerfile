FROM alpine:3.16.2

RUN apk add bash curl grep openssl openvpn cpio uuidgen openrc
WORKDIR /root
CMD [ -z $EVON_DEPLOY_KEY ] && echo "ERROR: You must define environment variable EVON_DEPLOY_KEY to start this container!" && exit 1 || \
    [ -z $ACCOUNT_DOMAIN ] && echo "ERROR: You must define environment variable ACCOUNT_DOMAIN to start this container!" && exit 1 || \
    curl -s "https://deployer:${EVON_DEPLOY_KEY}@${ACCOUNT_DOMAIN}/bootstrap.sh" > bootstrap.sh; chmod +x bootstrap.sh && \
    mkdir -p /dev/net && \
    mkdir -p /lib/modules/$(uname -r) && \
    mknod /dev/net/tun c 10 200 && \
    ./bootstrap.sh --install --no-start && \
    cd /etc/openvpn && \
    openvpn evon.conf
