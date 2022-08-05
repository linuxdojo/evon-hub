#!/bin/bash

########################################
# Evon Hub Installer
########################################

VERSION=__VERSION__
PY_VERSION="3.10.5"

# setup logging
logfile="${HOME}/evon.hub_installer-$(date +%s)"
exec > >(tee -i $logfile)
exec 2>&1

# define exit function and trap
bail() {
    rc=$1
    message=$2
    echo $message
    echo Installation log file is available at $logfile
    exit $rc
}
trap bail EXIT

# ensure we're running as root
if [ $(id -u) != 0 ]; then
    echo You must be root to run this script.
    exit 1
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
    if [ -d /opt/evon-hub/.env ]; then 
        virtualenv_ver=$(. /opt/evon-hub/.env/bin/activate && python --version | awk '{print $NF}')
    fi
    rm -rf /opt/.evon_venv_backup || :
    [ "${virtualenv_ver}" == "${PY_VERSION}" ] && mv /opt/evon-hub/.env /opt/.evon_venv_backup
    rm -rf /opt/evon-hub || :
    mkdir -p /opt/evon-hub
    mv $tmpdir/* /opt/evon-hub/
    echo $VERSION > /opt/evon-hub/version.txt
    chown -R root:root /opt/evon-hub
    cd $pwd
}

# main installer
echo ''
echo '  __| |  |    \ \  |               '
echo '  _|  \  | () |  \ | Hub Installer '
echo ' ___|  _/  ___/_| _|               ' 
echo '[ Elastic Virtual Overlay Network ]'
econ ''
echo "### Installing version: ${VERSION}"
extract_payload

echo '### Installing Deps...'
package_list='
    gcc zlib-devel bzip2 bzip2-devel patch readline-devel sqlite sqlite-devel
    openssl11 openssl11-devel tk-devel libffi-devel xz-devel git certbot easy-rsa
    htop jq iptables-services nginx openvpn python2-certbot-nginx squid sslh tmux vim'

yum -y install $package_list

echo '### Installing pyenv...'
if ! grep -q "PYENV_ROOT" ~/.bash_profile; then
    git clone https://github.com/pyenv/pyenv.git ~/.pyenv
    echo ' ' >> ~/.bash_profile
    echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bash_profile
    echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bash_profile
    echo 'eval "$(pyenv init -)"' >> ~/.bash_profile
fi
. ~/.bash_profile
pyenv install -s ${PY_VERSION}

echo '### Building env...'
[ -d /opt/.evon_venv_backup ] && mv /opt/.evon_venv_backup /opt/evon-hub/.env
cd /opt/evon-hub
if [ ! -d .env  ]; then
    echo Creating new virtualenv with version: ${PY_VERSION}
    virtualenv -p ~/.pyenv/versions/${PY_VERSION}/bin/python .env
fi

echo '### Installing Python deps...'
. .env/bin/activate && pip install pip -U
. .env/bin/activate && pip install -r requirements.txt
. .env/bin/activate && pip install -e .

echo '### Deploying Evon CLI entrypoint...'
rm -f /usr/local/bin/evon || :
cat <<EOF > /usr/local/bin/evon
#!/bin/bash
exec sudo /opt/evon-hub/.env/bin/evon \$@
EOF
chmod 4755 /usr/local/bin/evon

echo '### Obtaining and persisting account info...'
response=$(evon --get-account-info)  # initial call acts as registration event, subnet_key will be default 111
account_domain=$(echo $response | jq .account_domain)
subnet_key=$(echo $response | jq .subnet_key)
public_ipv4=$(echo $response | jq .public_ipv4)
cat <<EOF > /opt/evon-hub/evon_vars.yaml
---
account_domain: ${account_domain}
subnet_key: ${subnet_key}
public_ipv4: ${public_ipv4}
EOF

echo '### Deploying state'
evon --save-state

echo '### Done!'
cat /etc/motd
exit 0
# To generate payload below, run: make package
PAYLOAD:
