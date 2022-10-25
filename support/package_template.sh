#!/bin/bash

########################################
# Evon Hub Installer
########################################

VERSION=__VERSION__
PY_VERSION="3.10.5"
EVON_DOMAIN_SUFFIX=__EVON_DOMAIN_SUFFIX__
HOSTNAME_REGEX='^[a-z0-9]([-a-z0-9]*[a-z0-9])?$'
SUBNET_KEY_REGEX='^[0-9]{1,3}$'

# ensure we're running as root
if [ $(id -u) != 0 ]; then
    # replace self process owner with root
    exec sudo $0 $@
fi

# ensure we're running on AL2
if [ -r /etc/system-release ]; then
    grep -q "Amazon Linux release 2" /etc/system-release
    if [ $? -ne 0 ]; then
        echo 'Evon Hub must be installed on Amazon Linux 2'
        exit 1
    fi
else
    echo 'Unable to validate that this OS is Amazon Linux 2 (can not read /etc/system-release). Aborting.'
    exit 1
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
    # backup virtual env if version matches
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
    echo "
Options:

  -d, --domain-prefix DOMAIN_PREFIX
   Registers or retrieves your Evon account based on DOMAIN_PREFIX. This Hub
   will then be reachable at: <DOMAIN_PREFIX>.${EVON_DOMAIN_SUFFIX}.
   Omitting this option will cause this installer to interactively prompt for
   your domain prefix.

  -s, --subnet-key SUBNET_KEY
    Registers or retrieves your Evon account based on SUBNET_KEY.
    Your overlay network subnet will be 100.<SUBNET_KEY>.224.0/19 where
    SUBNET_KEY is between 64 and 127 inclusive. Default is 111 if omitted.
    "
}

# main installer
function show_banner() {
    echo ''
    echo '  __| |  |    \ \  |               '
    echo '  _|  \  | () |  \ | Hub Installer '
    echo " ___|  _/  ___/_| _| v${VERSION}   " 
    echo '[ Elastic Virtual Overlay Network ]'
    echo ''
}

function get_domain_prefix() {
    echo ""
    echo "Please choose a domain prefix for your Evon Hub."
	echo ""
    echo "Your Evon Hub will be reachable at domain:   <DOMAIN_PREFIX>.${EVON_DOMAIN_SUFFIX}"
    echo "Servers joined to this Hub will be assigned: <HOSTNAME>.<DOMAIN_PREFIX>.${EVON_DOMAIN_SUFFIX}"
    while [ "$success" != "true" ]; do
        echo ""
        echo -n "Enter your domain prefix (eg. mycompany) or ctrl-c to exit: "
        read domain_prefix
        echo "$domain_prefix" | grep -qE $HOSTNAME_REGEX
        if [ $? -ne 0 ]; then
            echo "ERROR: The provided domain prefix '${domain_prefix}' was not formatted correctly (it must conform to RFC 1123)"
        else
            echo ""
            echo "###############"
            echo "    Summary    "
            echo "###############"
            echo ""
            echo "Your Evon Hub will be reachable at url:    https://${domain_prefix}.${EVON_DOMAIN_SUFFIX}"
            echo "Your Evon overlay network subnet will be:  100.${subnet_key}.224.0/19"
            echo ""
            echo -n "Press enter to confirm or ctrl-c to abort: "
            read
            success="true"
        fi
    done
}

# Transform long options to short ones
for arg in "$@"; do
  shift
  case "$arg" in
    '--help')          set -- "$@" '-h'   ;;
    '--domain-prefix') set -- "$@" '-d'   ;;
    '--subnet-key')    set -- "$@" '-s'   ;;
    *)                 set -- "$@" "$arg" ;;
  esac
done

# Parse short options
OPTIND=1
while getopts ":hd:s:" opt; do
  case "$opt" in
    'h') show_banner; show_usage; exit 0 ;;
    'd') domain_prefix=$OPTARG ;;
    's') subnet_key=$OPTARG ;;
    '?') echo -e "ERROR: Bad option -$OPTARG.\nFor usage info, use --help"; exit 1 ;;
  esac
done
shift $(expr $OPTIND - 1) # remove options from positional parameters

# optargs validation
if [ ${#@} -ne 0 ]; then
    echo "Invalid arguments: $@"
    echo "For usage info, use --help"
    exit 1
fi

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


echo "### Installing version: ${VERSION}"
extract_payload

echo '### Installing dependencies...'
amazon-linux-extras install epel -y
[ ! -e /etc/yum.repos.d/MariaDB.repo ] && cat <<EOF > /etc/yum.repos.d/MariaDB.repo
[mariadb]
name = MariaDB
baseurl = https://mirror.mariadb.org/yum/10.5.17/centos7-amd64/
gpgkey = http://mirror.aarnet.edu.au/pub/MariaDB/yum/RPM-GPG-KEY-MariaDB
gpgcheck = 1
EOF
package_list='
    bzip2
    bzip2-devel
    certbot
    easy-rsa
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
    MariaDB-client
    MariaDB-devel
    MariaDB-server
    mlocate
    net-tools
    nginx
    openssl11-devel
    openvpn
    patch
    python2-certbot-nginx
    readline-devel
    sqlite-devel
    sslh
    tk-devel
    tmux
    vim
    xz-devel
    zlib-devel
'
yum -y install $package_list

echo '### Installing pyenv...'
if ! grep -q "PYENV_ROOT" ~/.bash_profile; then
    git clone https://github.com/pyenv/pyenv.git /opt/pyenv
    echo ' ' >> ~/.bash_profile
    echo 'export PYENV_ROOT="/opt/pyenv"' >> ~/.bash_profile
    echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bash_profile
    echo 'eval "$(pyenv init -)"' >> ~/.bash_profile
fi
. ~/.bash_profile
pyenv install -s ${PY_VERSION}
echo Done.

echo '### Building env...'
/opt/pyenv/versions/${PY_VERSION}/bin/python -m pip install pip -U
/opt/pyenv/versions/${PY_VERSION}/bin/python -m pip install virtualenv
[ -d /opt/.evon_venv_backup ] && mv /opt/.evon_venv_backup /opt/evon-hub/.env
cd /opt/evon-hub
if [ ! -d .env  ]; then
    echo Creating new virtualenv with version: ${PY_VERSION}
    /opt/pyenv/versions/${PY_VERSION}/bin/virtualenv -p /opt/pyenv/versions/${PY_VERSION}/bin/python .env
fi

echo '### Installing Python deps...'
. .env/bin/activate && \
    pip install pip -U && \
    pip install -r requirements.txt && \
    pip install -e . && \

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

echo '### Obtaining and persisting account info...'
account_info=$(evon --register "{\"domain-prefix\":\"${domain_prefix}\",\"subnet-key\":\"${subnet_key}\"}")
if [ $? -ne 0 ]; then
    echo "Error registering account:"
    echo $account_info
    echo ""
    echo Pease refer to the error above, check your domain prefix and/or subnet key and re-run this installer.
    exit 1
fi
iid=$(curl -s 'http://169.254.169.254/latest/dynamic/instance-identity/document')
account_domain=$(echo $account_info | jq .account_domain)
subnet_key=$(echo $account_info | jq .subnet_key)
public_ipv4=$(echo $account_info | jq .public_ipv4)
aws_region=$(echo $iid | jq .region)
aws_az=$(echo $iid | jq .availabilityZone)
ec2_id=$(echo $iid | jq .instanceId)
if [ -z "ec2_id" ]; then
    bail 1 "Failed to retrieve AWS EC2 Instance Identity Document information. Please retry by re-running this installer."
fi
cat <<EOF > /opt/evon-hub/evon_vars.yaml
---
account_domain: ${account_domain}
subnet_key: ${subnet_key}
public_ipv4: ${public_ipv4}
aws_region: ${aws_region}
aws_az: ${aws_az}
ec2_id: ${ec2_id}
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
rm -f /var/www/html/bootstrap.sh || :
evon --save-state
rc=$?
if [ $rc -ne 0 ]; then
    bail $rc "ERROR: Installation failed, please contact support at support@evon.link and provide the log file at path $logfile"
fi

echo '### Done!'
cat /etc/motd
bail 0
# To generate payload below, run: make package
PAYLOAD:
