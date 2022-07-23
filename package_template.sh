#!/bin/bash

########################################
# Evon Hub Installer
########################################

VERSION=__VERSION__

# setup logging
logfile="~/evon.hub_installer-$(date +%s)"
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
    cd /tmp
    rm -rf /opt/evon-hub || :
    mkdir -p /opt/evon-hub
    mv $tmpdir/* /opt/evon-hub/
    cd $pwd
}

# main installer
echo ""
echo "       ...................."
echo "+++===] Evon Hub Installer [===+++"
echo '       ````````````````````'

echo "### Installing version: ${VERSION}"
extract_payload

echo '### Installing Deps...'
yum -y install gcc zlib-devel bzip2 bzip2-devel patch readline-devel sqlite sqlite-devel openssl11 openssl11-devel tk-devel libffi-devel xz-devel git

echo '### Installing pyenv...'
if grep -q "# Pyenv Configuration" ~/.bash_profile; then
    echo pyenv installed, skipping
else
    git clone https://github.com/pyenv/pyenv.git ~/.pyenv
    echo ' ' >> ~/.bash_profile
    echo '# Pyenv Configuration' >> ~/.bash_profile
    echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bash_profile
    echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bash_profile
    echo 'eval "$(pyenv init -)"' >> ~/.bash_profile
fi
source ~/.bash_profile
pyenv install -s 3.10.5

echo '### Building env...'
cd /opt/evon-hub
if [ ! -d .env  ]; then
    virtualenv -p ~/.pyenv/versions/3.10.5/bin/python .env
fi

echo '## Installing Python deps...'
. .env/bin/activate && pip install -r requirements.txt

# To generate payload below, run: make package
exit 0
PAYLOAD:
