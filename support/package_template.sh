#!/bin/bash

########################################
# Evon Hub Installer
########################################

VERSION=__VERSION__
PY_VERSION="3.10.5"
EVON_DOMAIN_SUFFIX=__EVON_DOMAIN_SUFFIX__
HOSTNAME_REGEX='^[a-z0-9]([-a-z0-9]*[a-z0-9])?$'
DOMAINNAME_REGEX='^[a-z0-9]([-a-z0-9]*[a-z0-9])?\.[a-z0-9-]{1,63}(\.[a-z0-9-]{1,63})*$'
NON_RFC1918_IP_PATTERN='\b(?!10\.|192\.168\.|172\.(?:1[6-9]|2[0-9]|3[01])\.)(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(?:\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)){3}\b'
HWADDR_PATTERN='^[a-zA-Z0-9]{10}$'
SUBNET_KEY_REGEX='^[0-9]{1,3}$'
HOSTED_MODE=__HOSTED_MODE__


# ensure we're running as root
if [ $(id -u) != 0 ]; then
    if [ $HOSTED_MODE != "awsmp" ]; then
        echo You must be root to run this installer.
        exit 1
    fi
    # replace self process owner with root
    exec sudo $0 $@
fi

# set cert_type from evon_vars.yaml if present
unset previous_cert_type
export cert_type="certbot"
if [ -f /opt/evon-hub/evon_vars.yaml ]; then
    previous_cert_type="$(cat /opt/evon-hub/evon_vars.yaml | grep cert_type | awk -F": " '{print $NF}')"
    if [ "$previous_cert_type" ]; then
        export cert_type=$previous_cert_type
    fi
fi

# define payload extractor
function extract_payload() {
    # extract payload
    pwd=$(pwd)
    tmpdir=$(mktemp -d)
    cp $0 $tmpdir
    src=$(basename $0)
    cd $tmpdir
    match=$(grep --text --line-number '^PAYLOAD:$' $src | cut -d ':' -f 1)
    payload_start=$((match + 1))
    echo -n Extracting...
    tail -n +$payload_start $src | base64 -d | gunzip | cpio -id -H tar
    rm -f $src
    # backup virtual env dir if its python version matches the version that this script expects
    if [ -d /opt/evon-hub/.env ]; then 
        virtualenv_ver=$(. /opt/evon-hub/.env/bin/activate && python --version | awk '{print $NF}')
    fi
    rm -rf /opt/.evon_venv_backup || :
    [ "${virtualenv_ver}" == "${PY_VERSION}" ] && mv /opt/evon-hub/.env /opt/.evon_venv_backup
    # replace target dir
    rm -rf /opt/evon-hub || :
    mkdir -p /opt/evon-hub
    mv $tmpdir/* /opt/evon-hub/
    # create version file
    echo $VERSION > /opt/evon-hub/version.txt
    chown -R root:root /opt/evon-hub
    cd $pwd
}

function show_usage() {
    echo "Usage:"
    echo "  $0 [options]"
    echo -e "\nOptions:"

if [ "$HOSTED_MODE" == "awsmp" ]; then
    echo -n "
  -d, --domain-prefix DOMAIN_PREFIX
    Specify your DOMAIN_PREFIX for this Hub instance. This Evon Hub instance
    will be reachable at: <DOMAIN_PREFIX>.${EVON_DOMAIN_SUFFIX}
    Omitting this option will cause this installer to interactively prompt for
    your domain prefix.

  -s, --subnet-key SUBNET_KEY
    Specify your SUBNET_KEY for this Hub instance. Your overlay network
    subnet will become 100.<SUBNET_KEY>.224.0/19 where SUBNET_KEY must be
    between 64 and 127 inclusive. Default is 111 if this option is omitted.
"
elif [ "$HOSTED_MODE" == "selfhosted" ]; then
    echo -n "
  -d, --domain-prefix DOMAIN_PREFIX
    Specify your DOMAIN_PREFIX for this Hub instance. This Evon Hub instance
    will be reachable at: <DOMAIN_PREFIX>.${EVON_DOMAIN_SUFFIX}
    This option is required.

  -s, --subnet-key SUBNET_KEY
    Specify your SUBNET_KEY for this Hub instance. Your overlay network
    subnet will become 100.<SUBNET_KEY>.224.0/19 where SUBNET_KEY must be
    between 64 and 127 inclusive. Default is 111 if this option is omitted.

  -a, --hwaddr HARDWARE_ID
    Specify your HARDWARE_ID provided during registration of this selfhosted
    Evon Hub instance.
    This option is required.

  -i, --public-ip IPv4_ADDRESS
    If specified, set the public IPv4 address of this server to IPv4_ADDRESS,
    else automatically detect it. This address is used to create a DNS record
    for this Evon Hub at: <DOMAIN_PREFIX>.${EVON_DOMAIN_SUFFIX}
    Specifying this option will will save the provided IPv4_ADDRESS in the file
    \`/opt/.evon-hub.static_pub_ipv4\`. This file can be manually updated should
    the public IPv4 Address change.  Omitting this option or deleting the file
    \`/opt/evon-hub/.evon-hub.static_pub_ipv4\` will enable automatic detection
    of the current public IPv4 address, and the DNS record will be dynamically
    updated whenever a change is detected.
"
elif [ "$HOSTED_MODE" == "standalone" ]; then
    echo -n "
  -n, --domain-name DOMAIN_NAME
    Specify your DOMAIN_DOMAIN for this Hub instance. This Evon Hub instance
    will be reachable at this domain name, and connected servers will be
    given names in this DNS zone in the form \`<hostname>.<DOMAIN_NAME>\` where
    <hostname> is dynamically computed and optionally configurable per server.
    DOMAIN_NAME must contain at least two labels separated by a period, eg:
    \`example.com\`.
    This option is required.

  -s, --subnet-key SUBNET_KEY
    Specify your SUBNET_KEY for this Hub instance. Your overlay network
    subnet will become 100.<SUBNET_KEY>.224.0/19 where SUBNET_KEY must be
    between 64 and 127 inclusive. Default is 111 if this option is omitted.

  -i, --public-ip IPv4_ADDRESS
    If specified, set the public IPv4 address of this server to IPv4_ADDRESS,
    else automatically detect it. This address is used to create a DNS record
    for this Evon Hub at: <DOMAIN_PREFIX>.${EVON_DOMAIN_SUFFIX}
    Specifying this option will will save the provided IPv4_ADDRESS in the file
    \`/opt/.evon-hub.static_pub_ipv4\`. This file can be manually updated should
    the public IPv4 Address change.  Omitting this option or deleting the file
    \`/opt/evon-hub/.evon-hub.static_pub_ipv4\` will enable automatic detection
    of the current public IPv4 address, and the DNS record will be dynamically
    updated whenever a change is detected.

  -t, --cert-type [certbot|selfsigned]
    Default: certbot
    Use a CertBot/Let's Encrtypt CA managed certificate, or generate a self-signed.
    This certificate is used for the Web UI, REST API and OpenVPN. The last
    provided value is remembered for future runs of this installer if this option
    is subsequently omitted. This system must be internet facing if certbot is
    selected.
    *** WARNING ***
    If you swap between certbot managed and self-signed certificates, in subsequent
    runs of this installer, then any servers currently connected to this hub will
    need to be reconnected using an updated bootstrap script!
"
fi
}

# main installer
function show_banner() {
    if [ "$HOSTED_MODE" != "awsmp" ]; then
        hmbanner=$HOSTED_MODE
    fi
    echo ''
    echo '  __| |  |    \ \  |' ${hmbanner}
    echo '  _|  \  | () |  \ | Hub Installer'
    echo " ___|  _/  ___/_| _| v${VERSION}"
    echo '[ Elastic Virtual Overlay Network ]'
    echo ''
}

function get_domain_prefix() {
    echo ""
    echo "Please choose a domain prefix for your Evon Hub."
    echo ""
    echo "Your Evon Hub will be reachable at domain:   <DOMAIN_PREFIX>.${EVON_DOMAIN_SUFFIX}"
    while [ "$success" != "true" ]; do
        echo ""
        echo -n "Enter your domain prefix (eg. mycompany) or ctrl-c to exit: "
        read domain_prefix
        echo "$domain_prefix" | grep -qE $HOSTNAME_REGEX
        if [ $? -ne 0 ]; then
            echo "ERROR: The provided domain prefix '${domain_prefix}' was not formatted correctly (it must conform to RFC 1123)"
        else
            echo ""
            echo "################"
            echo "  Confirmation    "
            echo "################"
            echo ""
            echo "Your desired Evon Hub URL is:      https://${domain_prefix}.${EVON_DOMAIN_SUFFIX}"
            echo "Your Evon overlay network subnet:  100.${subnet_key}.224.0/19"
            echo ""
            echo "If you want to modify your overlay network subnet,"
            echo "abort and enter command: evon-deploy --help"
            echo ""
            echo -n "Press enter to confirm the above or ctrl-c to abort: "
            read
            success="true"
            echo "Deploying Evon Hub..."
        fi
    done
}


function is_al2() {
    if  [ -r /etc/system-release ]; then
        grep -q "Amazon Linux release 2" /etc/system-release
        if [ $? -eq 0 ]; then
            echo true
        else
            echo false
        fi
    else
        echo false
    fi
}


function assert_supported_distro() {
    # ensure the linux distro is supported for selfhosted and standalone modes
    declare -g os_version=0
    proceed=false
    if [[ -e /etc/almalinux-release || -e /etc/rocky-release || -e /etc/centos-release || -e /etc/redhat-release ]]; then
        os_version=$(grep -shoE '[0-9]+' /etc/redhat-release /etc/almalinux-release /etc/rocky-release /etc/centos-release | head -1)
        if [[ $os_version -ne 8 || $os_version -ne 9 ]]; then
            proceed=true
        fi
    fi
    if [ "$proceed" != "true" ]; then
        echo "Rocky Linux, AlmaLinux or equivalent distribution of version 8 or 9 is required to install Evon Hub."
        exit 1
    fi
}


# Transform long options to short ones
for arg in "$@"; do
  shift
  case "$arg" in
    '--help')          set -- "$@" '-h'   ;;
    '--domain-prefix') set -- "$@" '-d'   ;;
    '--domain-name')   set -- "$@" '-n'   ;;
    '--subnet-key')    set -- "$@" '-s'   ;;
    '--public-ipv4')   set -- "$@" '-i'   ;;
    '--hwaddr')        set -- "$@" '-a'   ;;
    '--cert-type')     set -- "$@" '-t'   ;;
    *)                 set -- "$@" "$arg" ;;
  esac
done

# Parse short options
OPTIND=1
while getopts ":hbt:d:s:i:a:n:" opt; do
  case "$opt" in
    'h') show_banner; show_usage; exit 0 ;;
    'b') base_build=true ;;
    'd') domain_prefix=$OPTARG ;;
    'n') domain_name=$OPTARG ;;
    's') subnet_key=$OPTARG ;;
    'i') public_ipv4_address=$OPTARG ;;
    'a') hwaddr=$OPTARG ;;
    't') export cert_type=$OPTARG ;;
    ':') echo -e "ERROR: Option -$OPTARG requires an argument.\nFor usage info, use --help"; exit 1 ;;
    '?') echo -e "ERROR: Bad option -$OPTARG.\nFor usage info, use --help"; exit 1 ;;
  esac
done
shift $(expr $OPTIND - 1) # remove options from positional parameters


### optargs validation

if [ ${#@} -ne 0 ]; then
    echo "Invalid arguments: $@"
    echo "For usage info, use --help"
    exit 1
fi

if [ "$cert_type" != 'certbot' ] && [ "$cert_type" != "selfsigned" ]; then
    echo "--cert-type/-t option must be set to either 'certbot' or 'selfsigned'"
    exit 1
elif [ "$previous_cert_type" ] && [ "$cert_type" != "$previous_cert_type" ]; then
    echo "    ,.,.,.,.,"
    echo "    :WARNING: "
    echo "    '\`'\`'\`'\`'"
        echo "    You have changed --cert-type/-t from its previous value of '$previous_cert_type' to '$cert_type'."
    echo "    If you continue, you will need to reconnect ALL connected servers to this Hub using a new bootstrap script,"
    echo "    as the newly generated certificate created by this operation will be used by OpenVPN."
    echo ""
    attempts=20
    echo -n "    Hit ctrl-c now to cancel, else continuing in $attempts seconds"
    while [ $attempts -gt 0 ]; do
        attempts=$((attempts-1))
        echo -n "."
        sleep 1
    done
    echo ""
fi

if [ "$HOSTED_MODE" == "awsmp" ]; then
    # we're running in awsmp (AWS Marketplace) mode, ensure we're on al2
    if [ "$(is_al2)" == "false" ]; then
        echo 'Amazon Linux 2 is required. Aborting.'
        exit 1
    fi
    # clear unused vars, set hosted vars
    public_ipv4_address=""
    hwaddr=""
    selfhosted="false"
    standalone="false"

elif [ "$HOSTED_MODE" == "selfhosted" ]; then

    # ensure the linux distro is supported
    assert_supported_distro

    if [ ! "$base_build" ]; then
        # we require hwaddr to be specified
        if [ -z "$hwaddr" ]; then
            echo 'ERROR: --hwaddr option is required'
            echo "For usage info, use --help"
            exit 1
        fi

        # validate hwaddr
        echo "$hwaddr" | grep -qE "$HWADDR_PATTERN"
        if [ $? -ne 0 ]; then
            echo "ERROR: The provided hwaddr '${hwaddr}' is invalid."
            exit 1
        fi

        # validate pub ipv4 address if supplied
        if [ "$public_ipv4_address" ]; then
            echo -n "$public_ipv4_address" | grep -qP $NON_RFC1918_IP_PATTERN
            if [ $? -ne 0 ]; then
                echo "ERROR: The provided IPv4_ADDRESS '${public_ipv4_address}' is invalid. It must be a public IPv4 address."
                echo "For usage info, use --help"
                exit 1
            fi
        fi
    fi

    # set hosted vars
    selfhosted="true"
    standalone="false"

elif [ "$HOSTED_MODE" == "standalone" ]; then

    # ensure the linux distro is supported
    assert_supported_distro

    # we're running in standalone mode
    if [ "$base_build" ]; then
        echo 'ERROR: -b option is not supported in standalone mode.'
        exit 1
    fi

    # validate and parse DOMAIN_NAME
    if [ -z "$domain_name" ]; then
        echo "ERROR: --domain-name option is required."
        echo "For usage info, use --help"
        exit 1
    fi
    echo "$domain_name" | grep -qE "$DOMAINNAME_REGEX"
    if [ $? -ne 0 ]; then
        echo "ERROR: The provided domain name '${domain_name}' was not formatted correctly (each label must conform to RFC 1123, minimum two labels are required)"
        echo "For usage info, use --help"
        exit 1
    fi
    # Extract the prefix up to the first dot
    domain_prefix="${domain_name%%.*}"
    # Extract the suffix after the first dot
    EVON_DOMAIN_SUFFIX="${domain_name#*.}"

    # set hosted vars
    if [ -f /opt/.evon-hub.hwaddr ]; then
        hwaddr="$(cat /opt/.evon-hub.hwaddr)"
    else
        hwaddr=$(tr -dc 'a-zA-Z0-9' < /dev/urandom | head -c 10)
    fi

    # set hosted vars
    selfhosted="true"
    standalone="true"
fi


### main installer

if [ "$base_build" ]; then
    echo '***** Applying base build only *****'
else
    if [ -z $subnet_key ]; then
        subnet_key=111
    else
        # subnet must be between 64 and 127 inclusive
        echo "$subnet_key" | grep -qE $SUBNET_KEY_REGEX
        if [ $? -ne 0 ] || [ $subnet_key -lt 64 ] || [ $subnet_key -gt 127 ]; then
            echo "ERROR: The provided subnet key '${subnet_key}' was not formatted correctly (it must be a number between 64 and 127 inclusive)"
            echo "For usage info, use --help"
            exit 1
        fi
    fi

    # start main installer
    show_banner

    echo "###############################################"
    echo "  Welcome to Evon Hub setup and registration!"
    echo "###############################################"

    if [ "$domain_prefix" ]; then
        echo "$domain_prefix" | grep -qE "$HOSTNAME_REGEX"
        if [ $? -ne 0 ]; then
            echo "ERROR: The provided domain prefix '${domain_prefix}' was not formatted correctly (it must conform to RFC 1123)"
            echo "For usage info, use --help"
            exit 1
        fi
    else
        if [ "${HOSTED_MODE}" == "selfhosted" ]; then
            echo 'ERROR: --domain-prefix option is required'
            echo "For usage info, use --help"
            exit 1
        fi
        # We arrive here if HOSTED_MODE == "awsmp" and no domain_prefix was specified.
        # We get the domain prefix interactively from the user.
        get_domain_prefix
    fi

    # setup logging
    logdir=/var/log/evon
    mkdir -p $logdir
    logfile="${logdir}/evon-hub_installer-$(date +%s)"
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
fi


echo Configured to use cert_type: $cert_type

echo "### Installing version: ${VERSION}"
extract_payload

echo '### Installing dependencies...'
set -e
package_list='
    bzip2
    bzip2-devel
    certbot
    conntrack-tools
    gcc
    git
    htop
    httpd-tools
    iproute
    iptables-services
    jq
    glibc-devel
    libcap
    libcap-devel
    libffi-devel
    mlocate
    net-tools
    nginx
    openvpn
    openvpn-devel
    patch
    readline-devel
    sqlite-devel
    tk-devel
    tmux
    vim
    xz-devel
    zlib-devel'
if [ "$(is_al2)" == "true" ]; then
    ###############
    # distro is al2
    ###############
    package_list="$package_list
        easy-rsa
        MariaDB-client
        MariaDB-devel
        MariaDB-server
        openssl11-devel
        python2-certbot-nginx
        sslh"
    rm -f /etc/yum.repos.d/MariaDB.repo
    amazon-linux-extras install epel -y
    cat <<EOF > /etc/yum.repos.d/MariaDB.repo
[mariadb]
name = MariaDB
baseurl = https://mirror.mariadb.org/yum/10.5/centos7-amd64/
gpgkey = http://mirror.aarnet.edu.au/pub/MariaDB/yum/RPM-GPG-KEY-MariaDB
gpgcheck = 1
EOF
    yum -y install $package_list
elif [ $os_version -eq 8 ]; then
    ###############
    # distro is el8
    ###############
    package_list="$package_list
        easy-rsa
        iptables-services
        kernel-modules-extra
        make
        mariadb
        mariadb-devel
        mariadb-server
        openssl-devel
        python3-certbot-nginx
        sslh
        tar
        vnstat"
    dnf -y install epel-release
    dnf -y install $package_list
else
    ###############
    # distro is el9
    ###############
    package_list="$package_list
        iptables-legacy
        iptables-legacy-devel
        iptables-services
        kernel-modules-extra
        make
        mariadb
        mariadb-devel
        mariadb-server
        openssl-devel
        python3-certbot-nginx
        tar
        vnstat"
    dnf config-manager --set-enabled crb
    dnf -y install epel-release
    dnf -y install $package_list
    dnf install -y \
        http://evon-supplemental.s3.ap-southeast-2.amazonaws.com/el9/sslh-1.21c-6.fc38.x86_64.rpm \
        http://evon-supplemental.s3.ap-southeast-2.amazonaws.com/el9/easy-rsa-3.1.5-1.fc38.noarch.rpm
fi
set +e

echo '### Installing pyenv...'
if ! grep -q "PYENV_ROOT" ~/.bash_profile; then
    echo Cloning pyenv git repo...
    rm -rf /opt/pyenv
    git clone https://github.com/pyenv/pyenv.git /opt/pyenv
    if [ $? -ne 0 ]; then
        bail 1 "ERROR: could not clone pyenv git repo at https://github.com/pyenv/pyenv.git"
    fi
    echo Configuring bash_profile...
    echo ' ' >> ~/.bash_profile
    echo 'export PYENV_ROOT="/opt/pyenv"' >> ~/.bash_profile
    echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bash_profile
    echo 'eval "$(pyenv init -)"' >> ~/.bash_profile
fi
echo "Ensuring Python ${PY_VERSION} is installed..."
. ~/.bash_profile
pyenv install -s ${PY_VERSION}
if [ $? -ne 0 ]; then
    bail 1 "ERROR: failed to install python version ${PY_VERSION} using pyenv. See above for error info."
fi
echo Done.

echo '### Building env...'
/opt/pyenv/versions/${PY_VERSION}/bin/python -m pip install pip -U --root-user-action=ignore
/opt/pyenv/versions/${PY_VERSION}/bin/python -m pip install virtualenv --root-user-action=ignore
[ -d /opt/.evon_venv_backup ] && mv /opt/.evon_venv_backup /opt/evon-hub/.env

cd /opt/evon-hub
if [ ! -d .env  ]; then
    echo Creating new virtualenv with version: ${PY_VERSION}
    /opt/pyenv/versions/${PY_VERSION}/bin/virtualenv -p /opt/pyenv/versions/${PY_VERSION}/bin/python .env
fi

# load evon env vars
source /opt/evon-hub/evon/.evon_env

if [ "$public_ipv4_address" ]; then
    echo "deploying static ipv4 address in /opt/.evon-hub.static_pub_ipv4"
    echo -n "$public_ipv4_address" > /opt/.evon-hub.static_pub_ipv4
fi

if [ "$hwaddr" ]; then
    echo "deploying /opt/.evon-hub.hwaddr file"
    echo -n "$hwaddr" > /opt/.evon-hub.hwaddr
fi

echo "deploying standalone hook script at path: ${STANDALONE_HOOK_PATH}"
standalone_hook_md5sum_path=$(dirname ${STANDALONE_HOOK_PATH})/.$(basename ${STANDALONE_HOOK_PATH}).md5sum
if [ ! -e ${STANDALONE_HOOK_PATH} ]; then
    # the example standalone hook script doesnt yet exist. Create it using packaged example version.
    cp evon/evon_standalone_hook_example ${STANDALONE_HOOK_PATH}
    chmod +x ${STANDALONE_HOOK_PATH}
    md5sum ${STANDALONE_HOOK_PATH} > ${standalone_hook_md5sum_path}
else
    if [ "$(cat ${standalone_hook_md5sum_path})" == "$(md5sum ${STANDALONE_HOOK_PATH})" ]; then
        # the example standalone hook script hasn't been modified. Remove and replace with current packaged version.
        rm -f ${STANDALONE_HOOK_PATH}_new >/dev/null 2>&1 || :
        rm -f ${STANDALONE_HOOK_PATH} ${standalone_hook_md5sum_path}
        cp evon/evon_standalone_hook_example ${STANDALONE_HOOK_PATH}
        chmod +x ${STANDALONE_HOOK_PATH}
        md5sum ${STANDALONE_HOOK_PATH} > ${standalone_hook_md5sum_path}
    else
        # the example standalone hook script has been modified. Copy the new one in place with _new suffix and warn user of update
        rm -f ${STANDALONE_HOOK_PATH}_new >/dev/null 2>&1 || :
        cp evon/evon_standalone_hook_example ${STANDALONE_HOOK_PATH}_new
        chmod +x ${STANDALONE_HOOK_PATH}_new
        new_hook_script_available=true
    fi
fi

echo '### Installing Python deps...'
. .env/bin/activate && \
    pip install pip -U && \
    pip install pip-tools && \
    pip-sync requirements.txt && \
    pip install -e . && \

if [ "$base_build" ]; then
    echo '***** Base build completed *****'
    exit 0
fi

# XXX the below can be improved using Django's management commands cli interface
echo '### Deploying Evon CLI entrypoints...'
rm -f /usr/local/bin/evon || :
cat <<EOF > /usr/local/bin/evon
#!/bin/bash
exec sudo /opt/evon-hub/.env/bin/evon \$@
EOF
rm -f /usr/local/bin/eapi || :
cat <<EOF > /usr/local/bin/eapi
#!/bin/bash
exec sudo /opt/evon-hub/.env/bin/eapi \$@
EOF
chmod 4755 /usr/local/bin/evon
chmod 4755 /usr/local/bin/eapi

if [ "$HOSTED_MODE" != "awsmp" ]; then

    # we're selfhosted/standalone, start and persist the selfhosted_shim service
    setenforce 0 || :
    sed -i 's/SELINUX=enforcing/SELINUX=disabled/g' /etc/selinux/config
    cd /opt/evon-hub/evon/selfhosted_shim
    make deploy
    cd -

    # also start and persist the vnstat service
    systemctl start vnstat
    systemctl enable vnstat

    if [ "$HOSTED_MODE" == "standalone" ]; then
        # We're specifically in standalone mode. Prepopulate values in evon_vars.yaml for API registration
        echo -en "---\naccount_domain: \"${domain_name}\"\nsubnet_key: ${subnet_key}\npublic_ipv4:" > /opt/evon-hub/evon_vars.yaml
    fi
fi

echo '### Obtaining and persisting account info...'
evon --register "{\"domain-prefix\":\"${domain_prefix}\",\"subnet-key\":\"${subnet_key}\"}"
if [ $? -ne 0 ]; then
    bail 1 "ERROR: Failed to register your Evon account, see above log for info."
fi
account_info=$(evon --get-account-info)
if [ $? -ne 0 ]; then
    echo "Error registering account:"
    echo $account_info
    echo ""
    bail 1 "ERROR: Failed to retrieve your Evon account, see above log for info."
fi
iid=$(curl -s 'http://169.254.169.254/latest/dynamic/instance-identity/document')
account_domain=$(echo $account_info | jq .account_domain)
subnet_key=$(echo $account_info | jq .subnet_key)
public_ipv4=$(echo $account_info | jq .public_ipv4)
aws_region=$(echo $iid | jq .region)
aws_az=$(echo $iid | jq .availabilityZone)
aws_account_id=$(echo $iid | jq .accountId)
ec2_id=$(echo $iid | jq .instanceId)
if [ -z "ec2_id" ]; then
    bail 1 "Failed to retrieve the Instance Identity Document information. Please retry by re-running this installer."
fi
cat <<EOF > /opt/evon-hub/evon_vars.yaml
---
account_domain: ${account_domain}
subnet_key: ${subnet_key}
public_ipv4: ${public_ipv4}
aws_account_id: ${aws_account_id}
aws_region: ${aws_region}
aws_az: ${aws_az}
ec2_id: ${ec2_id}
hosted_mode: ${HOSTED_MODE}
selfhosted: ${selfhosted}
standalone: ${standalone}
standalone_hook_path: ${STANDALONE_HOOK_PATH}
cert_type: ${cert_type}
EOF

echo '### Initialising DB and Evon Hub app...'
systemctl enable mariadb
systemctl start mariadb
mysql -uroot -e "
    CREATE DATABASE IF NOT EXISTS evon;
    GRANT ALL PRIVILEGES  ON evon.* TO 'evon'@'localhost' IDENTIFIED BY 'evon' WITH GRANT OPTION;
    FLUSH PRIVILEGES;
"
eapi migrate --noinput
eapi collectstatic --noinput

echo '### Configuring Hub and Users'
# disable debug mode
sed -i 's/DEBUG = True/DEBUG = False/g' /opt/evon-hub/eapi/settings.py
# create users, init config
useradd evonhub --shell /bin/false || :
cat <<EOF | eapi shell
from django.contrib.auth import get_user_model
import json
import requests
from hub import models
resp = requests.get('http://169.254.169.254/latest/dynamic/instance-identity/document')
User = get_user_model()  
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', '', json.loads(resp.text)['instanceId'])
if not User.objects.filter(username='deployer').exists():
    User.objects.create_user('deployer', is_staff=False)
models.Config.get_solo()
EOF
echo Done.

echo '### Deploying state'
evon --save-state
rc=$?
if [ $rc -ne 0 ]; then
    bail $rc "ERROR: Installation failed, please contact support at support@evonhub.com and provide the log file at path $logfile"
fi

# Check for and apply updates
update_available=$(evon --check-update --quiet | jq .update_available)
if [ "$update_available" == "true" ]; then
    echo "*** New update available, applying... ***"
    evon --update
    exit $?
fi

# Validate EC2 IAM Role has been setup correctly
if [ "${EVON_ENV}" != "dev" ]; then
    evon --iam-validate
    if [ $? -ne 0 ]; then
        echo "###############################"
        echo "  EC2 IAM Role Setup Required  "
        echo "###############################"
        echo ""
        echo "An IAM Role must be created in your AWS account and attached to this EC2 instance for Evon Hub to function correctly."
        echo "You only need to create the IAM role once. Please complete the following steps:"
        echo ""
        echo "1. Login to your AWS Management Console, ensure you're in the correct region, open EC2 Services and click Instances"
        echo "2. Select this EC2 instance with Instance ID ${ec2_id} and click Actions -> Security -> Modify IAM role"
        echo "3. Click Create new IAM role (or choose an existing one if you've completed these steps already), a new browser tab will open"
        echo "4. Click Create role -> select 'AWS service' and 'EC2', click Next -> select AWSMarketplaceMeteringFullAccess and click Next"
        echo "5. Provide a Role name (eg 'evon-hub') and click Create role"
        echo "6. In previous 'Modify IAM role' browser tab, click the refresh icon and choose the IAM role created in previous steps, click Update IAM role"
        echo "7. Validate you've created the role correctly by entering command: evon --iam-validate"
        echo "8. Finally, re-run this installer by entering command: $0 -d ${domain_prefix} -s ${subnet_key}"
        echo ""
        exit 1
    fi
fi

# finish
account_domain=$(echo ${account_domain} | sed 's/"//g')
ec2_id=$(echo ${ec2_id} | sed 's/"//g')
echo '### Done!'
echo ""
if [ "$new_hook_script_available" ]; then
    echo "========================================================================================"
    echo "NOTE:"
    echo "Updated standalone hook script example written to file '${STANDALONE_HOOK_PATH}_new'".
    echo "Review changes and modify your script at path '${STANDALONE_HOOK_PATH}' if needed."
    echo "========================================================================================"
    echo ""
fi
echo "##############################################################"
echo "              Setup and registration completed!"
echo "  Please browse to your Evon Hub Web UI using below details:"
echo ""
echo "     Your Evon Hub WebUI: https://${account_domain}"
echo "Default WebUI login (user / pass): admin / ${ec2_id}"
echo ""
echo "##############################################################"
bail 0

# Package payload
PAYLOAD:
