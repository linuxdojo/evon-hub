#!/bin/sh

########################################
# Evon Endpoint Server Bootstrap Script
########################################

# shim for script compatibility to ensure we're being interpreted by bash
if ! which bash >/dev/null 2>&1; then
    if grep -qs "Alpine" /etc/os-release; then
        apk add bash
        if [ $? -ne 0 ]; then
            echo "ERROR: Couldn't install bash. Please install bash manually and re-run this installer."
            exit 1
        fi
        bash $0 $@
        exit $?
    else
        echo "ERROR: bash is required for this installer."
        exit 1
    fi
elif ! which realpath >/dev/null 2>&1; then
    if [[ -e /etc/almalinux-release || -e /etc/rocky-release || -e /etc/centos-release || -e /etc/redhat-release ]]; then
        os_version=$(grep -shoE '[0-9]+' /etc/redhat-release /etc/almalinux-release /etc/rocky-release /etc/centos-release | head -1)
        if [ "$os_version" -eq 6 ]; then
            rpm -ivh http://evon-supplemental.s3.ap-southeast-2.amazonaws.com/el6/realpath-1.17-1.el6.rf.x86_64.rpm
            if [ $? -ne 0 ]; then
                echo "Failed to install realpath. Please install it manually and rerun this installer"
                exit 1
            fi
            exec $0 $@
        fi
    else
        echo "ERROR: The 'realpath' command is missing on this system. Please install it, then re-run this installer."
        exit 1
    fi
elif [ "$(basename $(realpath /proc/$$/exe))" != "bash" ] || cat /proc/$$/cmdline | grep -qE '^/bin/sh'; then
    bash $0 $@
    exit $?
fi


function custom_section() {
#################################################
# CUSTOM SECTION
#################################################

# Use this section of the script to perform any custom operations on the remote system as required,
# such as adding an SSH public key to a user's authorized keys file. See below for such an example.
# Uncomment and supply your own `ssh_pub_key` value to use it:

#username=root       # specify the user
#ssh_pub_key='ssh-rsa AAAAB3Nza...ovI8ksEmov'  # paste your own SSH public key to install
#echo "Installing SSH public key to ${username}'s authorized keys file..."
#homedir=$(getent passwd ${username} | cut -d: -f6)
#mkdir -p ${homedir}/.ssh
#chmod 700 ${homedir}/.ssh
#touch ${homedir}/.ssh/authorized_keys
#chmod 600 ${homedir}/.ssh/authorized_keys
#grep -q "${ssh_pubkey}" ${homedir}/.ssh/authorized_keys || echo -e "\n${ssh_pubkey}" >> ${homedir}/.ssh/authorized_keys
#echo Done.

#################################################
# END CUSTOM SECTION
#################################################
:
}


# set vars
VERSION="{{ evon_version }}"
EVON_HUB_PEER="100.{{ subnet_key }}.224.1"
ACCOUNT_DOMAIN="{{ account_domain }}"
SUBNET_KEY="{{ subnet_key }}"
UUID_REGEX='^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
HOSTNAME_REGEX='^[a-z0-9]([-a-z0-9]*[a-z0-9])?$'

# ensure we're running as root
if [ $(id -u) != 0 ]; then
    echo You must be root to run this installer.
    exit 1
fi


# ensure we're not running on the hub
if [ -e /opt/evon-hub/version.txt ]; then
    echo Evon Bootstrap can not be installed on your Evon Hub!
    echo This installer must be run on an endpoint system that you wish to join to your overlay network.
    exit 1
fi

# warn if we're running in WSL
if [ $(uname -r | sed -n 's/.*\( *Microsoft *\).*/\1/ip') ]; then
    echo '*** Warning: ***********************************************************************'
    echo 'This appears to be a WSL Linux environment which is not supported and may not work.'
    echo 'To connect Windows systems to your Evon Hub, use the PowerShell version of the'
    echo 'Bootstrap installer "boostrap.ps1" downloadable from your Evon Web Console at:'
    echo "  https://${ACCOUNT_DOMAIN}"
    echo '************************************************************************************'
    echo -n "Hit Ctrl-C to abort, else continuing in "
    count=5
    while [ $count -gt 0 ]; do
        echo -n "$count "
        ((count-=1))
        sleep 1
    done
    echo ""
fi

# detect distribution
if grep -qs "ubuntu" /etc/os-release; then
    os="ubuntu"
    if [[ -e /etc/upstream-release/lsb-release ]]; then
        # add support for Linux Mint
        os_version=$(grep 'DISTRIB_RELEASE' /etc/upstream-release/lsb-release | cut -d '=' -f 2 | tr -d '.')
    else
        os_version=$(grep 'VERSION_ID' /etc/os-release | cut -d '"' -f 2 | tr -d '.')
    fi
elif [[ -e /etc/debian_version ]]; then
    os="debian"
    os_version=$(grep -oE '[0-9]+' /etc/debian_version | head -1)
elif [[ -e /etc/sysconfig/ipoffice ]]; then
    os="ipoffice"
    # upstream is CentOS 7
    os_version=$(grep IPOFFICE_FULL_VERSION /etc/sysconfig/ipoffice | cut -d'"' -f2 | awk '{print $1}' | cut -d. -f1)
    FW_LINE='iptables -I INPUT -i tun0 -j ACCEPT'
    RC_FILE='/etc/rc.d/rc.local'
elif [[ -e /etc/almalinux-release || -e /etc/rocky-release || -e /etc/centos-release || -e /etc/redhat-release ]]; then
    os="centos"
    os_version=$(grep -shoE '[0-9]+' /etc/redhat-release /etc/almalinux-release /etc/rocky-release /etc/centos-release | head -1)
elif [[ -e /etc/fedora-release ]]; then
    os="fedora"
    os_version=$(grep -oE '[0-9]+' /etc/fedora-release | head -1)
elif grep -qs "Amazon Linux" /etc/os-release; then
    os="al"
    os_version=$(grep 'VERSION_ID' /etc/os-release | cut -d '"' -f 2 | tr -d '.')
elif grep -qs "openSUSE" /etc/os-release; then
    os="opensuse"
    os_version=$(grep 'VERSION_ID' /etc/os-release | cut -d '"' -f 2 | tr -d '.')
elif grep -qs "Alpine" /etc/os-release; then
    os="alpine"
    os_version=$(grep 'VERSION_ID' /etc/os-release | cut -d '"' -f 2 | tr -d '.')
    modprobe tun || :
elif grep -qs "Arch" /etc/os-release; then
    os="arch"
    os_version=$(grep 'VERSION_ID' /etc/os-release | cut -d '"' -f 2 | tr -d '.')
else
    echo "This installer seems to be running on an unsupported Linux distribution.
Supported distros are AlmaLinux, Alpine, Amazon Linux, Arch, CentOS, Debian, Fedora, RHEL, Rocky Linux, Ubuntu and openSUSE."
    exit 1
fi


# detect incompatibilities
if [[ "$os" == "ubuntu" && "$os_version" -lt 1804 ]]; then
    echo "Ubuntu 18.04 or higher is required to run this installer."
    exit 1
elif [[ "$os" == "ipoffice" && "$os_version" -lt 11 ]]; then
    echo "Avaya IPOffice major version 11 is required to run this installer."
    exit 1
elif [[ "$os" == "debian" && "$os_version" -lt 9 ]]; then
    echo "Debian 9 or higher is required to run this installer."
    exit 1
elif [[ "$os" == "centos" && "$os_version" -lt 6 ]]; then
    echo "RHEL/CentOS 6 or higher is required to run this installer."
    exit 1
elif [[ "$os" == "opensuse" && $(echo $os_version | cut -d. -f1) -lt 15  ]]; then
    echo "openSUSE major version 15 or higher is required to run this installer."
    exit 1
elif [[ ! -e /dev/net/tun ]] || ! ( exec 7<>/dev/net/tun ) 2>/dev/null; then
    echo "The system does not have the TUN device available which is required by this installer."
    exit 1
fi


# payload extractor function
function extract_payload() {
    extract_dir=$1
    cp $0 $extract_dir
    src=$(basename $0)
    cd $extract_dir
    match=$(grep --text --line-number '^PAYLOAD:$' $src | cut -d ':' -f 1)
    payload_start=$((match + 1))
    echo -n Extracting...
    tail -n +$payload_start $src | base64 -d | gunzip | cpio -id -H tar
    rm -f $src
    cd - >/dev/null
}

# curl function wrapper
function curl_wrapper() {
    if [[ "$os" == "centos" && "$os_version" -eq 6 ]]; then
        curl_extra_arg="-k"
    fi
    OUTPUT_FILE=$(mktemp)
    HTTP_CODE=$(curl ${curl_extra_arg} --silent --output $OUTPUT_FILE --write-out "%{http_code}" "$@")
    rc=$?
    if [ $rc != 0 ]; then
        echo "ERROR: curl returned non-zero return code $rc. See https://curl.se/libcurl/c/libcurl-errors.html for error code detail." > $OUTPUT_FILE
    elif [[ ${HTTP_CODE} -lt 200 || ${HTTP_CODE} -gt 299 ]] ; then
        if [ ${HTTP_CODE} -eq 401 ]; then
            echo "ERROR: Bad deploy key" > $OUTPUT_FILE
        elif [ ${HTTP_CODE} -eq 403 ]; then
            echo "ERROR: User associated with provided key is forbidden from installing bootstrap, 'deployer' key or a superuser key is required." > $OUTPUT_FILE
        else
            echo "ERROR: Got HTTP response code ${HTTP_CODE} from Evon Hub" > $OUTPUT_FILE
        fi
    fi
    cat $OUTPUT_FILE
    rm $OUTPUT_FILE
}

# sends encrypted openvpn secrets payload to Hub API for decryption based on API key, and stores decrypted cleartext to file if successful
function decrypt_secret() {
    evon_deploy_key=$1
    in_file=$2
    out_file=$3
    curl_wrapper -X POST "https://${ACCOUNT_DOMAIN}/api/bootstrap/decrypt" \
        -H "Authorization: Token ${evon_deploy_key}" \
        -F "data=@${in_file}" > ${out_file}
    if cat ${out_file} | grep -q ERROR; then
        echo  ""
        cat ${out_file}
        return 1
    fi
}


function show_usage() {
    echo "Usage:"
    echo "  $0 [options]"
    echo "
Options:

  -i, --install
    Install Evon Bootstrap (start and persist the OpenVPN connection to your
    Evon Hub)

  -u, --uninstall
    Uninstall Evon Bootstrap (stop and unpersist the OpenVPN connection to your
    Evon Hub)

  -d, --uuid <UUID>
    If not set, a unique UUID value will be auto-generated using the output of
    the command \`uuidgen\`, else <UUID> will be used. This value is stored
    locally and sent to your Evon Hub upon connection to identify this server.
    Evon Hub will map this value to a static auto-assigned IPv4 address on the
    overlay network. Connecting to Evon Hub using the same UUID will cause the
    server to always be assigned the same static IPv4 address. The value will be
    stored in the file: /etc/openvpn/evon.uuid
    Note: if /etc/openvpn/evon.uuid exists, the UUID located in that file will
    always be used and this option can not be specified. Remove this file before
    running bootstrap if you want to change the UUID (and the IPv4 overlay net
    address) for this server.

  -n, --hostname <HOSTNAME>
    If not set, a unique HOSTNAME value will be auto-generated using the output
    of the command \`uname -n\`, else <HOSTNAME> will be used. This value is
    stored locally and sent to your Evon Hub upon connection to provide it with
    the name of this server. This server will then be reachable at the public
    FQDN \`<HOSTNAME>.<domain-prefix>.evon.link\` where <domain-prefix> is your
    domain prefix that was chosen during registration. Should there be a conflict
    of hostnames on Evon Hub, the HOSTNAME will be auto-indexed, eg. HOSTNAME-1.
    HOSTNAME will be stored in the file /etc/openvpn/evon.uuid and can be changed
    at any time, and applied by restarting the OpenVPN service on this server.

  -e, --extra-config <FILE>
    Append extra OpenVPN config in <FILE> to the default Evon Hub OpenVPN
    config. Use this option if you need to tunnel through a proxy server by
    creating <FILE> with the following contents:

        http-proxy [proxy_address] [proxy_port] [none|basic|ntlm]
        <http-proxy-user-pass>
        [proxy_username]
        [proxy_password]
        </http-proxy-user-pass>

    Refer to the OpenVPN Reference Manual at https://openvpn.net for more info.

  -s, --no-start
    Deploy the OpenVPN configuration for connecting to your Evon Hub, but do not
    start/persist the service.

  -v, --version
    Show version and exit

  -h, --help
    This help text

Environment Variables:

  EVON_DEPLOY_KEY
    If set, the value will be used as the key for decrypting the OpenVPN config
    secrets during installation. If not set, you will be prompted for this key.
    Set this if non-interactive (unattended) installation is required. To
    retrieve the deploy key, visit your Evon Hub Admin site and copy the key
    for user \`deployer\` (or a superuser) at:
    https://${ACCOUNT_DOMAIN}/authtoken/tokenproxy/"
}


function show_banner() {
    echo ''
    echo '  __| |  |    \ \  |               '
    echo '  _|  \  | () |  \ | Bootstrap     '
    echo " ___|  _/  ___/_| _| v${VERSION}   "
    echo '[ Elastic Virtual Overlay Network ]'
    echo ''
}


function uninstall() {
    echo Stoppping and unpersisting OpenVPN connection to Evon Hub...
    if [ "$os" == "alpine" ]; then
        rc-update del openvpn default
        rc-service openvpn stop
    elif [[ "$os" == "centos" && "$os_version" -eq 6 ]]; then
        service openvpn stop
        chkconfig openvpn off
    else
        service_name="openvpn-client@evon"
        if [ "$os" == "opensuse" ]; then
            service_name="openvpn@evon"
        fi
        systemctl disable $service_name
        systemctl stop $service_name
    fi
    if [[ "$os" == "ipoffice" ]]; then
        sed -i "/${FW_LINE}/d" $RC_FILE
    fi
    echo Removing Evon OpenVPN config files...
    find /etc/openvpn | grep 'evon' | grep -v 'evon.uuid' | while read f; do
        echo Removing file: $f
        rm -f "$f"
    done
    if [ "$os" == "alpine" ] && [ -h /etc/openvpn/openvpn.conf ]; then
        symlink_target=$(readlink /etc/openvpn/openvpn.conf)
        if [ "$symlink_target" == "/etc/openvpn/evon.conf" ]; then
            echo Removing file: /etc/openvpn/openvpn.conf
            rm -f /etc/openvpn/evon.conf
        fi
    fi
    if [ -e /etc/openvpn/evon.uuid ]; then
        echo "NOTE: Not removing file /etc/openvpn/evon.uuid - please delete it manually if you're sure it is not needed."
    fi
    echo Uninastall done.
}

# Transform long options to short ones
for arg in "$@"; do
  shift
  case "$arg" in
    '--help')         set -- "$@" '-h'   ;;
    '--version')      set -- "$@" '-v'   ;;
    '--install')      set -- "$@" '-i'   ;;
    '--uninstall')    set -- "$@" '-u'   ;;
    '--no-start')     set -- "$@" '-s'   ;;
    '--uuid')         set -- "$@" '-d'   ;;
    '--hostname')     set -- "$@" '-n'   ;;
    '--extra-config') set -- "$@" '-e'   ;;
    *)                set -- "$@" "$arg" ;;
  esac
done

# Parse short options
OPTIND=1
while getopts ":hiud:ve:n:s" opt; do
  case "$opt" in
    'h') show_banner; show_usage; exit 0 ;;
    'i') evon_install=true ;;
    'u') evon_uninstall=true ;;
    's') evon_nostart=true ;;
    'd') evon_uuid=$OPTARG ;;
    'e') evon_extra=$OPTARG ;;
    'n') evon_hostname=$OPTARG ;;
    'v') echo $VERSION; exit 0 ;;
    '?') echo -e "ERROR: Bad option -$OPTARG.\nFor usage info, use --help"; exit 1 ;;
  esac
done
shift $(expr $OPTIND - 1) # remove options from positional parameters


# optargs validation
{% raw %}
if [ ${#@} -ne 0 ]; then
{% endraw %}
    echo "Invalid arguments: $@"
    echo "For usage info, use --help"
    exit 1
fi

if [ -z $evon_install ] && [ -z $evon_uninstall ]; then
    show_banner;
    echo "ERROR: Option --install or --uninstall must be specified."
    echo "For usage info, use --help"
    exit 1
fi

if [ "$evon_install" == "true" ] && [ "$evon_uninstall" == "true" ]; then
    echo "ERROR: Options are mutually exclusive: --install and --uninstall"
    exit 1
fi

if [ "$evon_uninstall" == "true" ] && [ "$evon_uuid" ]; then
    echo "ERROR: UUID can obly be provided with the --install option"
    exit 1
fi

if [ "$evon_uuid" ]; then
    echo "$evon_uuid" | grep -qE "$UUID_REGEX"
    if [ $? -ne 0 ]; then
        echo "ERROR: The provided UUID '${evon_uuid}' was not formatted correctly (it must conform to RFC 4122)"
        echo "For usage info, use --help"
        exit 1
    fi
fi

if [ "$evon_hostname" ]; then
    echo "$evon_hostname" | grep -qE "$HOSTNAME_REGEX"
    if [ $? -ne 0 ]; then
        echo "ERROR: The provided hostname '${evon_hostname}' was not formatted correctly (it must conform to RFC 1123)"
        echo "For usage info, use --help"
        exit 1
    fi
fi

if [ "$evon_uuid" ] && [ -e /etc/openvpn/evon.uuid ]; then
    echo "ERROR: You must remove /etc/openvpn/evon.uuid if you want to specify the UUID option."
    exit 1
fi

if [ "$evon_extra" ] && [ ! -r $evon_extra ]; then
    echo "ERROR: Can not read specified file: $evon_extra"
    exit 1
fi


# start main installer
show_banner

echo "Evon Bootstrap starting."

# setup logging
logdir=/var/log/evon
mkdir -p $logdir
logfile="${logdir}/evon_bootstrap-$(date +%s)"
exec > >(tee -i $logfile)
exec 2>&1
echo logging to file $logfile

# exit function
bail() {
    rc=$1
    message=$2
    echo $message
    exit $rc
}

# exit handler
end() {
    rc=$1
    echo ""
    echo Installation log file is available at $logfile
    exit $rc
}

# register exit handler
trap end EXIT

# uninstall if requested
if [ "$evon_uninstall" == "true" ]; then
    uninstall
    exit $?
fi

# Install deps
echo "Installing dependencies..."

if [[ "$os" == "debian" || "$os" == "ubuntu" ]]; then
    apt-get update
    apt-get install -y openvpn curl uuid-runtime jq iputils-ping
    rc=$?
elif [[ ( "$os" == "centos" && $os_version -eq 6  ) ]]; then
    which curl >/dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "The curl command is required on this system. Please manually install it and rerun this installer."
        exit 1
    fi
    # upgrade curl to compatible version
    curl -s http://evon-supplemental.s3.ap-southeast-2.amazonaws.com/el6/curl-7.19.7-53.el6_9.x86_64.rpm > /tmp/curl-7.19.7-53.el6_9.x86_64.rpm
    curl -s http://evon-supplemental.s3.ap-southeast-2.amazonaws.com/el6/libcurl-7.19.7-53.el6_9.x86_64.rpm > /tmp/libcurl-7.19.7-53.el6_9.x86_64
    curl -s http://evon-supplemental.s3.ap-southeast-2.amazonaws.com/el6/nss-3.44.0-7.el6_10.x86_64.rpm > /tmp/nss-3.44.0-7.el6_10.x86_64
    curl -s http://evon-supplemental.s3.ap-southeast-2.amazonaws.com/el6/nss-util-3.44.0-1.el6_10.x86_64.rpm > /tmp/nss-util-3.44.0-1.el6_10.x86_64.rpm
    curl -s http://evon-supplemental.s3.ap-southeast-2.amazonaws.com/el6/nspr-4.21.0-1.el6_10.x86_64.rpm > /tmp/nspr-4.21.0-1.el6_10.x86_64.rpm
    curl -s http://evon-supplemental.s3.ap-southeast-2.amazonaws.com/el6/nss-softokn-3.44.0-5.el6_10.x86_64.rpm > /tmp/nss-softokn-3.44.0-5.el6_10.x86_64.rpm
    curl -s http://evon-supplemental.s3.ap-southeast-2.amazonaws.com/el6/nss-softokn-freebl-3.44.0-6.el6_10.x86_64.rpm > /tmp/nss-softokn-freebl-3.44.0-6.el6_10.x86_64.rpm
    curl -s http://evon-supplemental.s3.ap-southeast-2.amazonaws.com/el6/nss-sysinit-3.44.0-7.el6_10.x86_64.rpm > /tmp/nss-sysinit-3.44.0-7.el6_10.x86_64.rpm
    curl -s http://evon-supplemental.s3.ap-southeast-2.amazonaws.com/el6/nss-tools-3.44.0-7.el6_10.x86_64.rpm > /tmp/nss-tools-3.44.0-7.el6_10.x86_64.rpm
    rpm -Uvh \
         /tmp/curl-7.19.7-53.el6_9.x86_64.rpm \
         /tmp/libcurl-7.19.7-53.el6_9.x86_64 \
         /tmp/nss-3.44.0-7.el6_10.x86_64 \
         /tmp/nss-util-3.44.0-1.el6_10.x86_64.rpm \
         /tmp/nspr-4.21.0-1.el6_10.x86_64.rpm \
         /tmp/nss-softokn-3.44.0-5.el6_10.x86_64.rpm \
         /tmp/nss-softokn-freebl-3.44.0-6.el6_10.x86_64.rpm \
         /tmp/nss-sysinit-3.44.0-7.el6_10.x86_64.rpm \
         /tmp/nss-tools-3.44.0-7.el6_10.x86_64.rpm
    which jq >/dev/null 2>&1
    if [ $? -ne 0 ]; then
        curl -s http://evon-supplemental.s3.ap-southeast-2.amazonaws.com/el6/jq-1.3-2.el6.x86_64.rpm > /tmp/jq-1.3-2.el6.x86_64.rpm
        rpm -ivh /tmp/jq-1.3-2.el6.x86_64.rpm 
    fi
    which jq >/dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "Failed to install the jq command. Please install it manually, then re-run this installer."
        exit 1
    fi
    which openvpn >/dev/null 2>&1
    if [ $? -ne 0 ]; then
        rm -rf /tmp/ovpnrpm >/dev/null 2>&1 || :
        mkdir -p /tmp/ovpnrpm
        curl -s http://evon-supplemental.s3.ap-southeast-2.amazonaws.com/el6/openvpn-2.4.9-1.el6.x86_64.rpm > /tmp/ovpnrpm/openvpn-2.4.9-1.el6.x86_64.rpm
        curl -s http://evon-supplemental.s3.ap-southeast-2.amazonaws.com/el6/lz4-r131-1.el6.x86_64.rpm > /tmp/ovpnrpm/lz4-r131-1.el6.x86_64.rpm
        curl -s http://evon-supplemental.s3.ap-southeast-2.amazonaws.com/el6/pkcs11-helper-1.11-3.el6.x86_64.rpm > /tmp/ovpnrpm/pkcs11-helper-1.11-3.el6.x86_64.rpm
        rpm -ivh /tmp/ovpnrpm/*.rpm
        rm -rf /tmp/ovpnrpm
    fi
    rpm -qa openvpn | grep -q openvpn
    if [ $? -ne 0 ]; then
        echo "Failed to install OpenVPN. Please install it manually, then re-run this installer."
        exit 1
    fi
elif [[ "$os" == "ipoffice" ]]; then
cat <<EOF > /etc/yum.repos.d/evon_deps.repo
[base]
name=CentOS-$releasever - Base
mirrorlist=http://mirrorlist.centos.org/?release=$releasever&arch=$basearch&repo=os&infra=$infra
#baseurl=http://mirror.centos.org/centos/$releasever/os/$basearch/
gpgcheck=1
enabled=0
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-CentOS-7

[updates]
name=CentOS-$releasever - Updates
mirrorlist=http://mirrorlist.centos.org/?release=$releasever&arch=$basearch&repo=updates&infra=$infra
#baseurl=http://mirror.centos.org/centos/$releasever/updates/$basearch/
gpgcheck=1
enabled=0
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-CentOS-7

[epel]
name=Extra Packages for Enterprise Linux 7 - $basearch
#baseurl=http://download.fedoraproject.org/pub/epel/7/$basearch
metalink=https://mirrors.fedoraproject.org/metalink?repo=epel-7&arch=$basearch
failovermethod=priority
enabled=0
gpgcheck=1
gpgkey=https://dl.fedoraproject.org/pub/epel/RPM-GPG-KEY-EPEL-7
EOF
    grep -qF -- "$FW_LINE" "$RC_FILE" || echo -e "\n$FW_LINE\n" >> "$RC_FILE"
    iptables -nvL INPUT | grep -qE '.+ACCEPT\s+all.+tun0.+0\.0\.0\.0\/0\s+0\.0\.0\.0\/0' || ${FW_LINE}
    yum --enablerepo=base,updates,epel install openvpn jq -y
    rc=$?
elif [[ ( "$os" == "centos" && $os_version -eq 7  ) ]]; then
    yum install -y epel-release
    yum install -y openvpn curl jq
    rc=$?
elif [[ "$os" == "centos" && $os_version -gt 7 ]]; then
    dnf install -y epel-release
    dnf install -y openvpn curl jq
    rc=$?
elif [[ "$os" == "al" ]]; then
    rpm -qa epel-release | grep -q epel-release || amazon-linux-extras install epel -y
    yum install -y openvpn curl jq
    rc=$?
elif [[ "$os" == "fedora" ]]; then
    dnf install -y openvpn curl jq
    rc=$?
elif [[ "$os" == "alpine" ]]; then
    if cpio 2>&1 | grep -q BusyBox; then
        echo "https://dl-cdn.alpinelinux.org/alpine/v$(cut -d'.' -f1,2 /etc/alpine-release)/community/" >> /etc/apk/repositories
        apk update
    fi
    apk add bash curl grep openssl openvpn cpio uuidgen openrc jq
    rc=$?
    modprobe tun || :
elif [[ "$os" == "opensuse" ]]; then
    zypper -n install openvpn curl jq
    rc=$?
elif [[ "$os" == "arch" ]]; then
    pacman --noconfirm -S openvpn curl cpio jq
    rc=$?
    extra_msg='You may need to run `pacman -Syu`'
fi
if [ $rc -ne 0 ]; then
    bail 1 "ERROR: Can't install dependencies, refer to error(s) above for reason. ${extra_msg}"
fi
echo Done.


# Configure OpenVPN
if [ "$evon_nostart" != "true"  ]; then
    attempts=5
    echo -n "Checking for an existing connection to Evon Hub"
    while [ $attempts -gt 0 ]; do
        attempts=$((attempts-1))
        echo -n "."
        ping -c1 -W1 $EVON_HUB_PEER >/dev/null 2>&1
        if [ $? -eq 0 ]; then
            echo -e "\nSuccess, link appears healthy, skipping OpenVPN configuration."
            installed=1
            break
        fi
    done
fi


# obtain realpath for evon_extra env var if specified
if [ "$evon_extra" ]; then
    evon_extra=$(realpath $evon_extra)
fi

if [ "$installed" != "1" ]; then
    [ "$evon_nostart" != "true" ] && echo -e "none found\nConfiguring OpenVPN..." || echo "Configuring OpenVPN..."
    tmpdir=$(mktemp -d)
    extract_payload $tmpdir
    cd $tmpdir
    # decrypt the secrets conf file.
    if [ -n "$EVON_DEPLOY_KEY" ]; then
        decrypt_secret ${EVON_DEPLOY_KEY} openvpn_secrets.conf.aes openvpn_secrets.conf
        if [ $? -ne 0 ]; then
            bail 1 "Error: Could not decrypt the OpenVPN config in this installer. Please check env var EVON_DEPLOY_KEY and re-run this script."
        fi
    else
        echo "Environment variable EVON_DEPLOY_KEY is not set. See --help for info about invoking this script non-interactively."
        while [ "$success" != "0" ]; do
            read -sp "Enter your Evon Deploy Key (text will not be echoed, ctrl-c to exit): " EVON_DEPLOY_KEY
            decrypt_secret ${EVON_DEPLOY_KEY} openvpn_secrets.conf.aes openvpn_secrets.conf
            success=$?
            [ "$success" != "0"  ] && echo Error decrypting, please check your deploy key and retry.
        done
        echo ""
    fi
    echo "Successfully extracted and decrypred installation payload, continuing..."
    rm -f openvpn_secrets.conf.aes

    #### deploy openvpn config files
    if [ "$os" == "opensuse" ] || \
        [ "$os" == "alpine" ] || \
        [[ ( "$os" == "centos" && $os_version -eq 6  ) ]]; then
        ovpn_conf_dir=/etc/openvpn
    else
        ovpn_conf_dir=/etc/openvpn/client
    fi

    # copy core config files to their proper locations
    echo Deploying Openvpn config...
    cp --remove-destination $tmpdir/openvpn_client.conf ${ovpn_conf_dir}/evon.conf
    if [ "$os" == "alpine" ]; then
        if [ -e /etc/openvpn/openvpn.conf ]; then
            symlink_target=$(readlink /etc/openvpn/openvpn.conf)
            if [ "$symlink_target" != "/etc/openvpn/evon.conf" ]; then
                echo "ERROR: /etc/openvpn/openvpn.conf already exists."
                echo "There seems to be existing OpenVPN configuration on this server. Rename or remove /etc/openvpn/openvpn.conf and re-run this installer."
                exit 1
            fi
        else
            ln -s /etc/openvpn/evon.conf /etc/openvpn/openvpn.conf
        fi
    fi
    cp --remove-destination $tmpdir/openvpn_secrets.conf ${ovpn_conf_dir}/evon_secrets.conf.inc

    # setup extra config file
    if [ "$evon_extra" ]; then
        echo "Copying provided extra config file $evon_extra to: ${ovpn_conf_dir}/evon_secrets.conf.inc"
        cp --remove-destination $evon_extra ${ovpn_conf_dir}/evon_extra.conf.inc
    elif [ ! -e ${ovpn_conf_dir}/evon_extra.conf.inc ]; then
        echo "Creating default extra config file: ${ovpn_conf_dir}/evon_extra.conf.inc"
cat <<EOF > ${ovpn_conf_dir}/evon_extra.conf.inc
# Place any extra OpenVPN config in this file if required. For exmample, to configure
# OpenVPN to use a proxy server, uncomment and edit the lines starting with ; below,
# and replace the parameters denoted by square brackets with your desired values.
# For reference, please refer to the OpenVPN documentation at:
# https://openvpn.net/community-resources/reference-manual-for-openvpn-2-4/

;http-proxy [proxy_address] [proxy_port] [none|basic|ntlm]

# Uncomment and set the below values (in square brackets) if required
;<http-proxy-user-pass>
;[username]
;[password]
;</http-proxy-user-pass>
EOF
    else
        echo "Not updating existing extra config file: ${ovpn_conf_dir}/evon_extra.conf.inc"
    fi

    # Create UUID file if it doesn't already exist
    echo Deploying UUID config...
    if [ ! -e /etc/openvpn/evon.uuid ]; then
        if [ -z $evon_uuid ]; then
            echo -n "Genrating new UUID..."
            evon_uuid=$(uuidgen)
            echo $evon_uuid
        else
            echo Using provided UUID: $evon_uuid
        fi
        # set hostname
        if [ -z $evon_hostname ]; then
            hostname=$(uname -n)
        else
            hostname=$evon_hostname
        fi
        echo -e "${evon_uuid}\n${hostname}" > /etc/openvpn/evon.uuid
        chmod 600 /etc/openvpn/evon.uuid
        [ "$os" == "arch" ] && chown openvpn /etc/openvpn/evon.uuid
    else
        echo Existing /etc/openvpn/evon.uuid file found, skipping.
    fi

    if [ "$evon_nostart" != "true" ]; then
        ##### Start and persist OpenVPN Client service
        echo "Starting OpenVPN Client service..."

        if [ "$os" == "alpine" ]; then
            uname -r | grep -q windows && touch /run/openrc/softlevel
            #TODO add `respawn_timeout=5` to /etc/init.d/openvpn to restart on failure
            rc-update add openvpn default
            rc-service openvpn start
        elif [[ ( "$os" == "centos" && $os_version -eq 6  ) ]]; then
            #TODO consider how to restart service on failure on these old sysvinit systems if required
            chkconfig openvpn on
            service openvpn stop || :
            service openvpn start
        else
            service_name="openvpn-client@evon"
            if [ "$os" == "opensuse" ]; then
                service_name="openvpn@evon"
            fi
            # add unit file override to always restart on error
            override_dir="/etc/systemd/system/${service_name}@evon.service.d"
            override_file="$override_dir/override.conf"
            mkdir -p "$override_dir"
cat <<EOF > "$override_file"
[Service]
Restart=always
RestartSec=5
EOF
            systemctl daemon-reload
            # estart and persist the evon client service
            systemctl enable $service_name
            systemctl stop $service_name || :
            systemctl start $service_name
        fi

        ##### Test OpenVPN connection
        attempts=20
        echo -n "Attempting to contact Evon Hub"
        while [ $attempts -gt 0 ]; do
            attempts=$((attempts-1))
            echo -n "."
            ping -c1 -W2 $EVON_HUB_PEER >/dev/null 2>&1
            if [ $? -eq 0 ]; then
                echo "success!"
                success=1
                break
            fi
        done
        if [ "$success" != "1" ]; then
            echo -e "\n"
            echo "Error: Unable to contact the Evon Hub VPN peer address at ${EVON_HUB_PEER}."
            echo "Please check syslog and the OpenVPN config in ${ovpn_conf_dir} and re-run this script"
            exit 1
        fi
        #### print status
        ipaddr=$(ip a | grep -E "inet 100.${SUBNET_KEY}" | awk '{print $2}')
        echo "Obtained VPN ip address: $ipaddr"
    else
        echo '--no-start specified, skipping start/persist of OpenVPN (only config has been deployed)'
    fi
else
    echo "Evon Hub Peer address at ${EVON_HUB_PEER} is reachable, OpenVPN seems to be already configured, skipping."
fi

##### clenaup tempdir
echo Cleanup tempdir...
cd
rm -rf $tempdir

##### run custom section
custom_section

# finish
echo "The Evon Hub connection setup has successfully completed!"
echo ""
echo "Note: If you wish to change the name of this Server in Evon Hub, edit line 2 of /etc/openvpn/evon.uuid and restart the OpenVPN service."
exit 0
PAYLOAD:
