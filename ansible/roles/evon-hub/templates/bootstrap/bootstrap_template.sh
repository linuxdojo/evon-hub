#!/bin/bash

########################################
# Evon Endpoint Server Bootstrap Script
########################################


VERSION={{ version }}

# Set the IPv4 address of the server-side VPN peer (reachable only if tunnel is up)
EVON_PEER=100.{{ subnet_key }}.252.1

# ensure we're running as root
if [ $(id -u) != 0 ]; then
    echo You must be root to run this installer.
    exit 1
fi

# ensure we're not running on the hub
if [ -e /opt/evon-hub/version.txt ]; then
    echo Evon bootstrap can not be installed on the Hub!
    echo This installer must be run on an endpoint system that you wish to join to your overlay network.
    exit 1
fi

# detect distribution
if grep -qs "ubuntu" /etc/os-release; then
    os="ubuntu"
    os_version=$(grep 'VERSION_ID' /etc/os-release | cut -d '"' -f 2 | tr -d '.')
    group_name="nogroup"
elif [[ -e /etc/debian_version ]]; then
    os="debian"
    os_version=$(grep -oE '[0-9]+' /etc/debian_version | head -1)
    group_name="nogroup"
elif [[ -e /etc/almalinux-release || -e /etc/rocky-release || -e /etc/centos-release ]]; then
    os="centos"
    os_version=$(grep -shoE '[0-9]+' /etc/almalinux-release /etc/rocky-release /etc/centos-release | head -1)
    group_name="nobody"
elif [[ -e /etc/fedora-release ]]; then
    os="fedora"
    os_version=$(grep -oE '[0-9]+' /etc/fedora-release | head -1)
    group_name="nobody"
elif grep -qs "Amazon Linux" /etc/os-release; then
    os="al"
    os_version=$(grep 'VERSION_ID' /etc/os-release | cut -d '"' -f 2 | tr -d '.')
    group_name="nobody"
elif grep -qs "openSUSE" /etc/os-release; then
    os="opensuse"
    os_version=$(grep 'VERSION_ID' /etc/os-release | cut -d '"' -f 2 | tr -d '.')
    group_name="nobody"
elif grep -qs "Alpine" /etc/os-release; then
    os="alpine"
    os_version=$(grep 'VERSION_ID' /etc/os-release | cut -d '"' -f 2 | tr -d '.')
    group_name="nobody"
else
    echo "This installer seems to be running on an unsupported distribution.
Supported distros are Alpine, Amazon Linux, Ubuntu, Debian, AlmaLinux, Rocky Linux, CentOS, Fedora and openSUSE."
    exit 1
fi

if [[ "$os" == "ubuntu" && "$os_version" -lt 1804 ]]; then
    echo "Ubuntu 18.04 or higher is required to run this installer."
    exit 1
fi

if [[ "$os" == "debian" && "$os_version" -lt 9 ]]; then
    echo "Debian 9 or higher is required to run this installer."
    exit 1
fi

if [[ "$os" == "centos" && "$os_version" -lt 7 ]]; then
    echo "CentOS 7 or higher is required to run this installer."
    exit 1
fi

if [[ "$os" == "opensuse" && $(echo $os_version | cut -d. -f1) -lt 15  ]]; then
    echo "openSUSE major version 15 higher is required to run this installer."
    exit 1
fi

if [[ ! -e /dev/net/tun ]] || ! ( exec 7<>/dev/net/tun ) 2>/dev/null; then
    echo "The system does not have the TUN device available.
TUN needs to be enabled before running this installer."
    exit 1
fi

# setup logging
logdir=/var/log/evon
mkdir -p $logdir
logfile="${logdir}/evon_bootstrap-$(date +%s)"
exec > >(tee -i $logfile)
exec 2>&1

# define exit function and handler
bail() {
    rc=$1
    message=$2
    echo $message
    exit $rc
}

end() {
    rc=$1
    echo ""
    echo Installation log file is available at $logfile
    exit $rc
}

# register exit handler
trap end EXIT


# curl function wrapper
curlf() {
    OUTPUT_FILE=$(mktemp)
    HTTP_CODE=$(curl --silent --output $OUTPUT_FILE --write-out "%{http_code}" "$@")
    rc=$?
    if [ $rc != 0 ]; then
        echo "ERROR: curl returned non-zero return code: $rc" > $OUTPUT_FILE
    elif [[ ${HTTP_CODE} -lt 200 || ${HTTP_CODE} -gt 299 ]] ; then
        if [ ${HTTP_CODE} -eq 401 ]; then
            echo "ERROR: Bad password" > $OUTPUT_FILE
        else
            echo "ERROR: Got HTTP response code ${HTTP_CODE}" > $OUTPUT_FILE
        fi
    fi
    cat $OUTPUT_FILE
    rm $OUTPUT_FILE
}


# decrypt key function
get_decrypt_key() {
    deploy_key=$1
    data=$(curlf -u "deployer:${deploy_key}" "https://{{ account_domain }}/deploy_key")
    if echo $data | grep -q ERROR; then
        echo $data
    else
        echo $(echo -n $data | md5sum | awk '{print $1}')
    fi
}


# prep tempdir
tmpdir="/tmp/evon_bootstrap"
rm -rf $tmpdir
mkdir $tmpdir

# define payload extractor
function extract_payload() {
    cp $0 $tmpdir
    src=$(basename $0)
    cd $tmpdir
    match=$(grep --text --line-number '^PAYLOAD:$' $src | cut -d ':' -f 1)
    payload_start=$((match + 1))
    tail -n +$payload_start $src | base64 -d | gunzip | cpio -idv -H tar
    cd -
}


# main installer
echo ''
echo '  __| |  |    \ \  |               '
echo '  _|  \  | () |  \ | Bootstrap     '
echo " ___|  _/  ___/_| _| v${VERSION}   " 
echo '[ Elastic Virtual Overlay Network ]'
echo ''

#TODO use getopts
if [ "$1" == "--uninstall" ]; then
    #TODO Fix the below...
    echo "Uninstalling..."
    if [ "$distro" == "centos8" ]; then
        systemctl stop openvpn-client@evon
        dnf -y remove openvpn
    elif [ "$distro" == "centos7" ]; then
        systemctl stop openvpn-client@evon
        yum -y remove openvpn
    else
        service openvpn stop
        yum -y remove openvpn
    fi
    echo "Done."
    exit 0
elif [ "$1" == "--help" ]; then
    echo "Usage:"
    echo "  $0 [--help] [--uninstall] "
    echo "Options:"
    echo "  <no args>       Install bootstrap (start and persist the OpenVPN connection to your Evon Hub)"
    echo "  --uninstall     Uninstall bootstrap config (stop and unpersist the OpenVPN connection to your Evon Hub)"
    echo "  --help          This help text"
    echo "Environment Variables:"
    echo "  EVON_DEPLOY_KEY If set, the value will be used as the key for decrypting the OpenVPN config."
    echo "                  If not set, you will be prompted for this key."

    exit 0
elif [ "$1" != "" ]; then
    echo "Unknown argument: $1"
    echo "Use --help for help."
    exit 1
fi


##### Install OpenVPN if required
echo "Installing OpenVPN..."
which openvpn >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "OpenVPN already installed, skipping."
else
    if [[ "$os" == "debian" || "$os" == "ubuntu" ]]; then
        apt-get update
        apt-get install -y openvpn curl
    elif [[ "$os" == "al" ]]; then
        yum install -y epel-release
        yum install -y openvpn curl
    elif [[ "$os" == "centos" ]]; then
        dnf install -y epel-release
        dnf install -y openvpn curl
    elif [[ "$os" == "fedora" ]]; then
        dnf install -y openvpn curl
    elif [[ "$os" == "alpine" ]]; then
        apk add openvpn
        apk add curl
    elif [[ "$os" == "opensuse" ]]; then
        zypper -n install openvpn curl
    fi
    if [ ! $? -eq 0 ]; then
        bail 1 "Error: Can't install OpenVPN, refer to error(s) above for reason. You may install OpenVPN yourself and re-run this script."
    fi
fi
echo Done.


#TODO persist openvpn

##### Configure OpenVPN if required (skip if we can ping the server peer)
attempts=5
echo -n "Checking for an existing connection to evon-hub"
while [ $attempts -gt 0 ]; do
    attempts=$((attempts-1))
    echo -n "."
    ping -c1 -W1 $EVON_PEER >/dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "Success, link appears healthy, skipping OpenVPN configuration."
        installed=1
        break
    fi
done

if [ "$installed" != "1" ]; then
    echo -e "none found\nConfiguring OpenVPN..."
    extract_payload
    cd $tmpdir
    # decrypt the secrets conf file.
    if [ -n "$EVON_DEPLOY_KEY" ]; then
        DECRYPT_KEY=$(get_decrypt_key "$EVON_DEPLOY_KEY")
        openssl enc -md sha256 -d -pass "pass:${DECRYPT_KEY}" -aes-256-cbc -in openvpn_secrets.conf.aes -out openvpn_secrets.conf 2>/dev/null
        if [ $? -ne 0 ]; then
            bail 1 "Error: Could not decrypt the OpenVPN config in this installer. Please check env var EVON_DEPLOY_KEY and re-run this script."
        fi
    else
        while [ "$success" != "0" ]; do
            read -sp "Enter your Evon Deploy Key (text will not be echoed, ctrl-c to exit): " EVON_DEPLOY_KEY
            DECRYPT_KEY=$(get_decrypt_key "$EVON_DEPLOY_KEY")
            if echo $DECRYPT_KEY | grep -q ERROR; then
                echo $DECRYPT_KEY
                continue
            fi
            openssl enc -md sha256 -d -pass "pass:${DECRYPT_KEY}" -aes-256-cbc -in ${tmpdir}/openvpn_secrets.conf.aes -out ${tmpdir}/openvpn_secrets.conf 2>/dev/null
            success=$?
            [ "$success" != "0"  ] && echo Error decrypting, please check the Deploy Key and retry.
        done
    fi

    #### deploy openvpn config files
    exit 1  # XXX Continue here...
    if [ "$distro" == "centos8" ] || [ "$distro" == "centos7" ]; then
        ovpn_conf_dir=/etc/openvpn/client
    else
        ovpn_conf_dir=/etc/openvpn
    fi
    cp --remove-destination $tmpdir/openvpn_secrets.conf $ovpn_conf_dir/openvpn_secrets.conf.inc
    cp --remove-destination $tmpdir/openvpn_client.conf $ovpn_conf_dir/openvpn_client.conf.inc
    [ -e $ovpn_conf_dir/openvpn_proxy.conf.inc ] \
        && echo "$ovpn_conf_dir/openvpn_proxy.conf.inc already exists, not overwriting as it may contain existing proxy settings." \
        || cp $tmpdir/openvpn_proxy.conf $ovpn_conf_dir/openvpn_proxy.conf.inc
    [ -e $ovpn_conf_dir/evon.conf ] && rm -f $ovpn_conf_dir/evon.conf
    ln -s $ovpn_conf_dir/openvpn_client.conf.inc $ovpn_conf_dir/evon.conf
    # Create UUID file if it doesn't already exist
    [ -e /etc/openvpn/evon.uuid ] \
        || echo -e "endpoint-$(uuidgen)\nnull" > /etc/openvpn/evon.uuid
    cd -
    echo -e "Current contents of OpenVPN Proxy Configuration ($ovpn_conf_dir/openvpn_proxy.conf.inc) is:\n"
    cat $ovpn_conf_dir/openvpn_proxy.conf.inc | sed 's/^/    /'
    # Prompt for editing proxy settings if $EVON_DEPLOY_KEY is not defined (be non-interactive if it is and don't prompt)
    if [ -z "$EVON_DEPLOY_KEY" ]; then
        echo -n "Would you like to edit the above file before we attempt to start OpenVPN? (y/N): "
        read response
        if [ "${response,,}" == "y" ]; then
            echo Launching editor...
            vi $ovpn_conf_dir/openvpn_proxy.conf.inc
        fi
    fi

    ##### Start and persist OpenVPN Client service
    echo "Starting OpenVPN Client service..."
    if [ "$distro" == "centos8" ] || [ "$distro" == "centos7" ]; then
        systemctl enable openvpn-client@evon
        systemctl stop openvpn-client@evon || :
        systemctl start openvpn-client@evon
    else
        chkconfig openvpn on
        service openvpn stop || :
        service openvpn start
    fi

    ##### Test OpenVPN connection
    attempts=15
    echo -n "Attempting to contact evon VPN server peer"
    while [ $attempts -gt 0 ]; do
        attempts=$((attempts-1))
        echo -n "."
        ping -c1 -W3 $EVON_PEER >/dev/null 2>&1
        if [ $? -eq 0 ]; then
            echo "success!"
            success=1
            break
        fi
    done
    if [ "$success" != "1" ]; then
        echo -e "\n"
        echo "Error: Unable to contact the EVON Server VPN peer address at ${EVON_PEER}."
        echo "Please check syslog and the OpenVPN config in $ovpn_conf_dir and re-run this script"
        exit 1
    fi
else
    echo "Server VPN Peer address at ${EVON_PEER} is reachable, OpenVPN seems to be already configured, skipping."
fi

##### clenaup tempdir
echo Cleanup tempdir...
rm -rf $tempdir

#### print status
#FIXME find ip address below in a distro-independent way...
ipaddr=$(cat /var/log/messages | grep openvpn | grep "ip addr add" | tail -n1 | awk '{print $(NF-2)}')
echo "Obtained VPN ip address: $ipaddr"
echo "The Evon-Hub connection setup has successfully completed!"

exit 0
PAYLOAD:
