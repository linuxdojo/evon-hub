#!/usr/bin/env python3

#################################
#
# EVON Deployment Mapper
#
#################################


from multiprocessing import Pool
from pathlib import Path
import logging.handlers
import subprocess
import ipaddress
import traceback
import textwrap
import logging
import signal
import glob
import time
import json
import sys
import os

import route53
import dotenv

# load env vars from .env file
dotenv.load_dotenv(dotenv_path=Path(os.path.dirname(os.path.realpath(__file__))) / '.env')

# number of concurrent ssh connections to deployments for hostname retrieval
NPROCS = 10
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
ZONE_ID = os.environ.get("ROUTE53_ZONE_ID")
IGNORED_RECORDS = {'_': 'evon.link.', 'www': 'www.evon.link.'}
CCD = "/etc/openvpn/ccd"
CLIENTS_CACHE = None
POOL_CONFIG_PATH = "/etc/openvpn/server/server_tcp-scope.conf"

# setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = logging.handlers.SysLogHandler(address = '/dev/log')
fmt = logging.Formatter(fmt=f'{os.path.basename(__file__)}[%(process)d]: %(levelname)s: %(message)s')
handler.setFormatter(fmt)
logger.addHandler(handler)
logger.addHandler(logging.StreamHandler(sys.stdout))


def get_openvpn_clients():
    """
    Returns a dict of {"CN": "VPN-IP-ADDR"} pairs
    Caches result and returns it for every subsequent call to this function
    """
    global CLIENTS_CACHE
    if CLIENTS_CACHE:
        return CLIENTS_CACHE
    clients = {}
    cmd = """sudo cat /etc/openvpn/server/openvpn-status_{tcp,udp}.log | grep -E '^CLIENT_LIST' | grep endpoint- | awk -F, '{print $2 ":" $4}'"""
    p = subprocess.Popen(cmd, shell=True, close_fds=True, \
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = p.stdout.read().decode('UTF-8').strip()
    for line in output.split('\n'):
        if ":" not in line:
            continue
        cn, ip = line.split(":")
        clients[cn] = ip
    CLIENTS_CACHE = clients
    return clients


def get_alive_openvpn_clients():
    """
    Enumerate openvpn clients from server status files and validate health via ping
    Returns a list of VPN IP addresses for connected WFO endpoints (ie. whose CN begins with "endpoint-")
    """
    ip_addresses = " ".join(list(get_openvpn_clients().values()))
    clients = []
    cmd = f"""nmap -n -sP -oG - {ip_addresses} | grep "Status: Up" | awk '{{print $2}}' | sort"""
    p = subprocess.Popen(cmd, shell=True, close_fds=True, \
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = p.stdout.read().decode('UTF-8')
    if not "No targets were specified" in output:
        for line in output.split('\n'):
            line.strip() and clients.append(line.strip())
    return clients


def sync_persist_ip_addresses(expiry_days=30):
    """
    Creates or updates OpenVPN CCD config files containing static ip address assignments for any first-seen WFO endpoints
    If CCD file already exists, only the `last_seen` value will be udpated to current epoch
    Deletes CCD config whose last_seen exceeds `expiry_days` days
    """
    ccd_template = textwrap.dedent("""        # client: {cn}
        # last_seen: {timestamp}
        ifconfig-push {local_ip} {peer_ip}
        push "route 10.111.0.1 255.255.255.255"
        """)
    timestamp = int(time.time())
    clients = get_openvpn_clients()
    for cn in clients:
        local_ip = clients[cn]
        peer_ip = ".".join(local_ip.split(".")[:-1] + [(str(int(local_ip.split(".")[3]) - 1))])
        ccd_path = os.path.join(CCD, cn)
        if os.path.isfile(ccd_path):
            # ccd file already exists, update its last_seen time
            with open(ccd_path) as f:
                lines = f.readlines()
            # log warning if endpoint ip address somehow changed
            prev_ip = [l.strip() for l in lines if l.find("ifconfig") != -1].pop().split()[-2]
            if local_ip != prev_ip:
                # should only happen if a tcp endpoint becomes a udp one and vice versa.
                logger.warning(f"Found mismatching ip address for client '{cn}': was {prev_ip}, but now is {local_ip}.")
            # write new timestamp to ccd file, preserving all other lines
            lines[1] = lines[1].rsplit(" ", 1)[0] + f" {timestamp}\n"
            data = "".join(lines)
            with open(ccd_path, "w") as f:
                f.write(data)
        else:
            # create new ccd file for client
            with open(ccd_path, "w") as f:
                f.write(ccd_template.format(cn=cn, timestamp=timestamp, local_ip=local_ip, peer_ip=peer_ip))
    # remove CCD files that have expired
    for fn in glob.glob(f"{CCD}/endpoint-*"):
        with open(fn) as f:
            timestamp = int([l.strip() for l in f.readlines() if l.find("last_seen") != -1].pop().split()[-1])
        delta = time.time() - timestamp
        if delta > expiry_days * 24 * 60 * 60:
            os.unlink(fn)


def update_pool_config(pool_cfg_path):
    bounce_required = False
    pool_template = textwrap.dedent("""        # this file is auto-generated, do not edit manually
        ifconfig-pool {start_ip} 10.111.254.251
        """)
    with open(pool_cfg_path) as f:
        current_start_ip = [l.split()[1] for l in f.readlines() if l.find("ifconfig-pool") != -1].pop()
    # calculate new start_ip
    client_ip_addresses = list(get_openvpn_clients().values())
    highest_ip = str(sorted([str(ipaddress.ip_address(i)) for i in client_ip_addresses], key = ipaddress.IPv4Address).pop())
    new_start_ip = str(ipaddress.ip_address(highest_ip) + 2)
    if current_start_ip != new_start_ip:
        with open(pool_cfg_path, "w") as f:
            f.write(pool_template.format(start_ip=new_start_ip))
            bounce_required = True
    return bounce_required


def get_hostname(ipaddr):
    """
    SSH into ipaddr and retrieve hostname, lowerified
    """
    cmd = ("ssh -i /home/openiq/.ssh/id_rsa-evon -o UserKnownHostsFile=/dev/null"
           " -o PasswordAuthentication=no -o ConnectTimeout=5 "
           f"-o StrictHostKeyChecking=no {ipaddr} -l root 'hostname'")
    p = subprocess.Popen(cmd, shell=True, close_fds=True, \
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p.wait()
    if p.returncode == 0:
        output = p.stdout.read().decode('UTF-8').strip()
    else:
        logger.warning(f'Received non-zero return code from SSH when evaluating hostname for {ipaddr}, using dashed IPv4 address as hostname')
        output = ipaddr.replace(".", "-")
    output = output.lower()
    err = p.stderr.read().decode('UTF-8').strip()
    for line in err.split('\n'):
        if not "Warning: Permanently added" in line:
            logger.warning(f"{line.strip()}")
    return output, ipaddr


def get_inventory():
    """
    Return a dict of fqdn:vpn_ip_address for all connected clients
    """
    inventory = {}
    clients = get_alive_openvpn_clients()
    p = Pool(NPROCS)
    with p:
        results = p.map(get_hostname, clients)
    if not results:
        return inventory
    for hostname, ipaddr in results:
        if hostname in inventory or hostname in IGNORED_RECORDS.keys():
            logger.warning(f'hostname "{hostname}" is duplicate or reserved, using dashed IPv4 address as hostname')
            hostname = ipaddr.replace(".", "-")
        inventory[f"{hostname}.evon.link"] = ipaddr
    return inventory


def retrieve_saved_inventory(zone):
    """
    Fetches records from AWS Route53 and returns a FQDN->IPv4 mapping of all deployments
    """
    saved_inventory = {}
    for record_set in zone.record_sets:
        if record_set.name in IGNORED_RECORDS.values():
            # These records are managed outside of this system
            continue
        saved_inventory[record_set.name[:-1]] = record_set.records.pop()
    return saved_inventory


def save_inventory(zone, changes):
    """
    CRUD function for AWS Route53 records for deployments FQDN's
    """
    # create new records
    for fqdn in changes['new']:
        target = changes['new'][fqdn]
        zone.create_a_record(
            name=f'{fqdn}.',
            values=[target],
            ttl=60,
            )
        logger.info(f"Created new record: {fqdn}->{target}")
    # update existing records
    for fqdn in changes['updated']:
        target = changes['updated'][fqdn]
        record_set = [rs for rs in zone.record_sets if rs.name == f"{fqdn}."].pop()
        record_set.records = [target]
        record_set.save()
        logger.info(f"Updated record: {fqdn}->{target}")
    # delete removed records
    for fqdn in changes['removed']:
        record_set = [rs for rs in zone.record_sets if rs.name == f"{fqdn}."].pop()
        record_set.delete()
        logger.info(f"Deleted record: {fqdn}")


def get_inventory_changes(previous_inventory, new_inventory):
    """
    diff old and new inventories returning a dictionary of changed state
    """
    changes = {
        'new': {},
        'removed': {},
        'updated': {},
        'unchanged': {}
        }
    for host in new_inventory:
        if host not in previous_inventory:
            changes['new'][host] = new_inventory[host]
        elif previous_inventory[host] != new_inventory[host]:
            changes['updated'][host] = new_inventory[host]
        else:
            changes['unchanged'][host] = new_inventory[host]
    for host in previous_inventory:
        if host not in new_inventory:
            changes['removed'][host] = previous_inventory[host]
    return changes


def publish_inventory(inventory):
    """
    Publish inventory for retrieval via http request
    """
    with open("/tmp/inventory", "w") as f:
        data = json.dumps(inventory).replace(", ", "\n,") + "\n"
        f.write(data)
    os.system("sudo mv -f /tmp/inventory /var/www/html >/dev/null 2>&1")


def bounce_vpn_server():
    cmd = r"""echo $(ps aux | grep -E '/usr/sbin/openvpn.+server_tcp.conf' | grep -v grep | awk '{print $2}')"""
    p = subprocess.Popen(cmd, shell=True, close_fds=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    pid = p.stdout.read().decode('UTF-8').strip()
    try:
        pid = int(pid)
    except Exception as e:
        logger.error(f"Failed to cast {pid} to an integer while attempting to obtain PID of OpenVPN server..")
    if p.returncode:
        logger.error(f"Got rc={p.returncode} while attempting to find PID of OpenVPN server. Output was: {pid}")
    else:
        logger.info(f"Sending SIGHUP to pid: {pid}")
        os.kill(pid, signal.SIGHUP)


if __name__ == "__main__":
    try:
        logger.info("Starting...")
        # create Route53 connection
        conn = route53.connect(
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY
            )
        zone = conn.get_hosted_zone_by_id(ZONE_ID)
        logger.info("Retrieving saved inventory...")
        previous_inventory = retrieve_saved_inventory(zone)
        logger.info(f"Saved inventory: {previous_inventory}")
        logger.info("Retrieving latest inventory...")
        inventory = get_inventory()
        logger.info("Computing changes since last inventory update...")
        changes = get_inventory_changes(previous_inventory, inventory)
        logger.info("Current Inventory:")
        logger.info(json.dumps(inventory))
        logger.info("Changes since last inventory update:")
        logger.info(json.dumps(changes))
        if changes["new"] or changes["removed"] or changes["updated"]:
            logger.info("Updating Route53...")
            save_inventory(zone, changes)
            logger.info("Publishing inventory to webserver...")
            publish_inventory(inventory)
        else:
            logger.info("No changes, skipping Route53 update.")
        logger.info("Syncing/persisting static client IP addresses...")
        sync_persist_ip_addresses()
        logger.info("Updating VPN client IP address pool...")
        bounce_required = update_pool_config(POOL_CONFIG_PATH)
        if bounce_required:
            logger.info("Pool start address has changed, sending SIGHUP to OpenVPN server.")
            bounce_vpn_server()
        else:
            logger.info("Pool start address is unchanged.")
        logger.info("Reloading Squid config for blacklist freshness...")
        cmd = "sudo systemctl reload squid"
        p = subprocess.Popen(cmd, shell=True, close_fds=True, \
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output = p.stdout.read().decode('UTF-8')
        output.strip() and logger.info(output)
        logger.info("Done.")
    except Exception as e:
        trace = traceback.format_exc()
        logger.error(trace)
        raise e

