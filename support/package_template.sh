#!/bin/bash

########################################
# Evon Hub Installer
########################################

VERSION=__VERSION__
PY_VERSION="3.10.5"

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

# setup logging
logdir=/var/log/evon
mkdir -p $logdir
logfile="${logdir}/evon-hub_installer-$(date +%s)"
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

# main installer
echo ''
echo '  __| |  |    \ \  |               '
echo '  _|  \  | () |  \ | Hub Installer '
echo ' ___|  _/  ___/_| _|               ' 
echo '[ Elastic Virtual Overlay Network ]'
echo ''
echo "### Installing version: ${VERSION}"
extract_payload

echo '### Installing Deps...'
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
    iptables-services
    jq
    libffi-devel
    MariaDB-client
    MariaDB-devel
    MariaDB-server
    mlocate
    nginx
    openssl-devel
    openvpn
    patch
    python2-certbot-nginx
    readline-devel
    squid
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
    ~/.pyenv/versions/3.10.5/bin/virtualenv -p ~/.pyenv/versions/${PY_VERSION}/bin/python .env
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

echo '### Initialising DB...'
systemctl enable mariadb
systemctl start mariadb
mysql -uroot -e "
    CREATE DATABASE IF NOT EXISTS evon;
    GRANT ALL PRIVILEGES  ON evon.* TO 'evon'@'localhost' IDENTIFIED BY 'evon' WITH GRANT OPTION;
    FLUSH PRIVILEGES;
"
eapi migrate --noinput

echo '### Obtaining and persisting account info...'
# initial call to --get-account-info acts as registration event, subnet_key will be default "111".
# TODO: use --set-inventory with subnet_key as input param
account_info=$(evon --get-account-info)
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
