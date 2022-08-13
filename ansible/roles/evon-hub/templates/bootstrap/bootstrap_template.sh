#!/bin/bash

########################################
# Evon Endpoint Server Bootstrap Script
########################################


VERSION={{ version }}

# Set the IPv4 address of the server-side VPN peer (reachable only if tunnel is up)
EVON_PEER=100.{{ subnet_key }}.252.1

# setup logging
logfile="/root/evon.link_bootstrap-$(date +%s)"
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
    echo Installation log file is available at $logfile
    exit $rc
}

# ensure we're running as root
if [ $(id -u) != 0 ]; then
    echo You must be root to run this installer.
    exit 1
fi

# ensure we're not running on the hub
if [ -e /etc/evon-hub/version.txt ]; then
    echo Evon bootstrap can not be installed on the Hub!
    echo This installer must be run on an endpoint system that you wish to join to your overlay network.
    exit 1
fi

# detect old 2.x kernel
if [[ $(uname -r | cut -d "." -f 1) -lt 3  ]]; then
    echo "This installer requires Linux kernel version 3.x or higher"
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
else
    echo "This installer seems to be running on an unsupported distribution.
Supported distros are Amazon Linux, Ubuntu, Debian, AlmaLinux, Rocky Linux, CentOS, Fedora and openSUSE."
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

# register exit handler
trap end EXIT

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
    rm -f /etc/profile.d/evon_proxy.sh
    echo "Note: You must log out and back in to remove the http proxy env vars"
    echo "Done."
    exit 0
elif [ "$1" == "--help" ]; then
    echo "Usage:"
    echo "  $0 [--help] [--uninstall] "
    echo "Options:"
    echo "  <no args>      Install bootstrap (start and persist the OpenVPN connection to your Evon Hub)"
    echo "  --uninstall    Uninstall bootstrap config (stop and unpersist the OpenVPN connection to your Evon Hub)"
    echo "  --help         This help text"
    echo "Environment Variables:"
    echo "  EVON_USERNAME, EVON_PASSWORD"  
    echo "                   If set, these values will be used as the Evon admin username and password required for this installation."
    echo "                 If either is not set, you will be prompted for the username and password."
    exit 0
elif [ "$1" != "" ]; then
    echo "Unknown argument: $1"
    echo "Use --help for help."
    exit 1
fi

##### Create Evon service account
#TODO create service user, add to sudoers, add ssh pub key
echo "Installing the evon SSH public key to root's authorized keys file..."
evon_pubkey='ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC/hKS2hDz8kupeoFSn8CMqeBGt+YqBT9U4FHA4ZV2dnO7jMlCr7nSF6tLPNptf8Ohh9e2w1sRHb8w2VCGvZ/Us/H7e93VAs86hU/7tS7gy97YnUIFmWru7K2aXWlAyhW5FouUD5Zs/7A9ys1bhvhUIbzGYiCDITWrErdaeJAHjZpIvdEHZi9zU560qUZ/2zelrWFGnSEMn9Y53gzKMjVCdxkF3g5lnB92+IkkeyRpWDn7Nb7uf/CRvaE59/2UWx0FF+HtKJ7yFJYjgqht0qP2HLcjA/COUShMlEIc3vpUgi5TK53si14IH/+lKBrl+lPJ4JkWBm5UpuWs9Hj7G9hICwHUMUOW5ONJbSsTF43sKYM1/lgHaujBCED7wvvI3LkKUX4Eb/0Egu3usDXMNZpgLtlh5c+uG+oLe/k/VfYH2XhkzvvsY+m1/9GHtFizfdgJr92uq75SH/mHrvjr3jGY2m98tjNli9rPV9OPWqRc0Zb89Wp0k/qzlkRF9LCy6Vgk= admin@evon.link'
mkdir -p /root/.ssh
chmod 700 /root/.ssh
touch /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys
grep -q "${evon_pubkey}" /root/.ssh/authorized_keys || echo -e "\n${evon_pubkey}" >> /root/.ssh/authorized_keys
echo Done.

##### Install OpenVPN if required
echo "Installing OpenVPN..."
if [ "$distro" == "centos8" ] || [ "$distro" == "centos7" ]; then
    package_manager=dnf
else
    package_manager=yum
fi
[ "$distro" == "centos7" ] && yum -y install epel-release
which openvpn >/dev/null 2>&1 && echo "OpenVPN already installed, skipping." || $package_manager -y install openvpn
if [ ! $? -eq 0 ]; then
    echo "Error: Can't install OpenVPN, refer to error(s) above for reason. You may install it yourself and re-run this script."
    if [ "$distro" == "centos8" ]; then
        echo '
Tips:

To configure DNF with a proxy server, enter the following lines (HTTP Basic Auth support only):

    export http_proxy=http://<username>:<password>@<proxy_host>:<proxy_port>
    export https_proxy=$http_proxy

or, if proxy requires NTLM auth,  edit /etc/dnf/dnf.conf and add the following lines:

    proxy=http://<host>:<port>  # Mandatory
    proxy_username=<username>   # Optional
    proxy_password=<password>   # Optional
    proxy_auth_method=basic     # Optional, change to 'ntlm' if required
    #Note that thes settings can be undone after evon VPN link is established as evon Squid proxy can be used instead.

To install OpenVPN manually, type:

    sudo dnf install -y openvpn
'
    else
        echo '
Tip:

To Install OpenSSH on CentOS6 deployments, enter the below lines. This assumes you have internet access either directly or via proxy.
Replace XXX below with the evon HTTP username and password.

    export evon_HTTP_USERNAME=XXX
    export evon_HTTP_PASSWORD=XXX
    mkdir -p /tmp/ovpninst
    cd /tmp/ovpninst
    wget --no-check-certificate https://${evon_HTTP_USERNAME}:${evon_HTTP_PASSWORD}@evon.link/support/el6/lz4-r131-1.el6.x86_64.rpm
    wget --no-check-certificate https://${evon_HTTP_USERNAME}:${evon_HTTP_PASSWORD}@evon.link/support/el6/openvpn-2.4.9-1.el6.x86_64.rpm
    wget --no-check-certificate https://${evon_HTTP_USERNAME}:${evon_HTTP_PASSWORD}@evon.link/support/el6/pkcs11-helper-1.11-3.el6.x86_64.rpm
    rpm -ivh *.rpm

To configure Yum with a proxy server, enter the following lines (HTTP Basic Auth support only):

    export http_proxy=http://<username>:<password>@<proxy_host>:<proxy_port>
    export https_proxy=$http_proxy

To fix Yum on CentOS6 WFO deployments due to end-of-life repositories, run as root:

    cp -r /etc/yum.repos.d /etc/yum.repos.d-backup_$(date +%s) # take a backup
    curl https://www.getpagespeed.com/files/centos6-eol.repo --output /etc/yum.repos.d/CentOS-Base.repo
    yum remove -y epel-release
    find /etc/yum.repos.d/centos-digium* | while read r; do mv $r ${r}_off; done
    yum install -y https://archives.fedoraproject.org/pub/archive/epel/6/x86_64/epel-release-6-8.noarch.rpm

Note on CentOS7, you must first install epel-release via command:

    yum install -y epel-release

To install OpenVPN manually, type:

    yum -y install openvpn
'
    fi
    exit 1
fi
echo Done.

##### Configure OpenVPN if required (skip if we can ping the server peer)
attempts=5
echo -n "Checking for an existing connection to evon hub"
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
    if [ -n "$EVON_SECRET" ]; then
        openssl enc -d -pass "pass:${EVON_SECRET}" -aes-256-cbc -in openvpn_secrets.conf.aes -out openvpn_secrets.conf 2>/dev/null
        if [ $? -ne 0 ]; then
            echo "Error: env var EVON_SECRET does not contain the correct evon secret string. Please change it and re-run this script."
            exit 1
        fi
    else
        echo "Enter EVON secret key below (ctrl-c to exit installer)..."
        while [ "$success" != "0" ]; do
            openssl enc -d -aes-256-cbc -in openvpn_secrets.conf.aes -out openvpn_secrets.conf 2>/dev/null
            success=$?
            [ "$success" != "0"  ] && echo Error decrypting, please check the secret key and retry.
        done
    fi

    #### deploy openvpn config files
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
    # Prompt for editing proxy settings if $EVON_SECRET is not defined (be non-interactive if it is and don't prompt)
    if [ -z "$EVON_SECRET" ]; then
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

##### Configure the evon Squid Proxy system-wide
echo "Configuring the evon Squid Proxy..."
cat <<EOF > /etc/profile.d/evon_proxy.sh.off
export http_proxy=http://${EVON_PEER}:3128
export https_proxy=http://${EVON_PEER}:3128
export no_proxy=
EOF
echo ""
echo "If you wish to add proxy exclusions, please edit /etc/profile.d/evon_proxy.sh.off and add them to the 'no_proxy' variable."
echo "For documentation see https://www.gnu.org/software/wget/manual/html_node/Proxies.html"
echo ""

##### clenaup tempdir
echo Cleanup tempdir...
rm -rf $tempdir

#### print status
ipaddr=$(cat /var/log/messages | grep openvpn | grep "ip addr add" | tail -n1 | awk '{print $(NF-2)}')
echo "Notes regarding evon Squid Proxy:"
echo ""
echo '    - Usage of the Squid proxy on evon.link is disabled by default. To temporarily enable it for your current shell, type:'
echo '          source /etc/profile.d/evon_proxy.sh.off'
echo ""
echo '    - To permanently enable it for all future shell sessions, type:'
echo '          mv /etc/profile.d/evon_proxy.sh{.off,}'
echo ""
echo '      Ensure no other script is overwriting the http_proxy or https_proxy env vars (eg. from within ~/.bashrc).'
echo '      You can always perform the above command to override these env vars for the current shell session.'
echo ""
echo '    - To permanently disable it again, run the following command:'
echo '          mv /etc/profile.d/evon_proxy.sh{,.off}'

echo ""
echo "Obtained VPN ip address: $ipaddr"
echo "The evon connection setup has successfully completed!"

exit 0
PAYLOAD:
