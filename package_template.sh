#!/bin/bash

########################################
# Evon Hub Installer
########################################

# setup logging
logfile="/root/evon.hub_installer-$(date +%s)"
exec > >(tee -i $logfile)
exec 2>&1

# get the absolute path of this script and set pwd
SCRIPTDIR="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P  )"
cd $SCRIPTDIR

# define exit function and trap
bail() {
    rc=$1
    message=$2
    echo $message
    echo Installation log file is available at $logfile
    cd $SCRIPTDIR
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

# prep tempdir
tmpdir="/tmp/evon-hub_installer"
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
echo ""
echo "       ...................."
echo '+++===] Evon Hub Installer [===+++'
echo '       ````````````````````'

# To generate payload below, run: make package
exit 0
PAYLOAD:
