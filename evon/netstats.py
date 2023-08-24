#!/usr/bin/env python

from collections import defaultdict
import datetime
import os
import json
import subprocess

import django
os.environ['DJANGO_SETTINGS_MODULE'] = 'eapi.settings'  # noqa
django.setup()  # noqa

from evon.evon_api import get_usage_limits  # noqa
from evon.cli import EVON_API_URL, EVON_API_KEY  # noqa
from evon.log import get_evon_logger  # noqa
from hub.models import User, UserProfile, Server  # noqa


logger = get_evon_logger()


def get_interfaces(tun_only=True):
    """
    returns a list of non-loopback interfaces
    """
    # just shell out, as python's psutil requires root/capabilities to read flags like LOOPBACK
    cmd = "ip link show | grep -E '^[0-9]' | grep -v LOOPBACK | cut -d: -f2 | xargs"
    p = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
    stdout_err = p.stdout.read().decode("utf-8").strip()
    result = stdout_err.split()
    if tun_only:
        result = [e for e in result if "tun" in e.lower()]
    return result


def get_user_count():
    """
    Returns current user count (less 2, for admin and deployer) on the hub
    """
    return User.objects.count() - 2


def get_server_count():
    """
    Returns current server count
    """
    return Server.objects.count()


def get_shared_device_count():
    """
    returns current shared user devices count
    """
    return UserProfile.objects.filter(shared=True).count()


def get_data_used_in_month():
    """
    returns data used in month in MB, rounded
    """
    bytes_used = 0
    for interface in get_interfaces():
        cmd = f"vnstat {interface} --oneline b"
        p = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
        stdout_err = p.stdout.read().decode("utf-8").strip()
        if "not enough data" in stdout_err.lower() or "error" in stdout_err.lower():
            continue
        bytes_used += int(stdout_err.split(";")[9])
    return int(round(bytes_used / 1024 / 1024))


def get_data_used_per_day():
    """
    Returns daily data used in current month in MB in format:
    {"<day_of_month> <3_letter_month>": "<mb_used>", ...}
    """
    first_day_of_month_ts = f"{datetime.datetime.now().strftime('%Y-%m')}-01 00:00"
    cmd = f'vnstat --begin "{first_day_of_month_ts}" --json d'
    p = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
    stdout_err = p.stdout.read().decode("utf-8")
    try:
        all_stats = json.loads(stdout_err)["interfaces"]
    except Exception:
        return {}
    result = defaultdict(int)
    all_interfaces = get_interfaces()
    for interface_stats in all_stats:
        if interface_stats.get("name") in all_interfaces:
            for day_data in interface_stats["traffic"]["day"]:
                month_num = str(day_data["date"]["month"])
                month_short_name = datetime.datetime.strptime(month_num, "%m").strftime("%b")
                day = day_data["date"]["day"]
                key = f"{day} {month_short_name}"
                val = int(round(day_data["tx"] / 1024 / 1024))
                result[key] += val
    return dict(result)  # oerdered since Python 3.7


def apply_throttle(mbps=0):
    if mbps:
        logger.info(f"throttling all interfaces to {mbps}Mbps")
        cmd = f"""for if in $(ip -br link | awk '$1 != "lo" {{print $1}}'); do /opt/evon-hub/.env/bin/tcset --device ${{if}} --rate {mbps}Mbps; done"""
    else:
        # unset throttles
        logger.info("removing all bandwidth throttles")
        cmd = """for if in $(ip -br link | awk '$1 != "lo" {print $1}'); do /opt/evon-hub/.env/bin/tcdel --device ${if} --all; done"""
    logger.debug(f"running command: {cmd}")
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
    rc = p.wait()
    output = p.stdout.read().decode()
    logger.debug(f"command rc: {rc}")
    logger.debug(f"command stdout_and_stderr: {output}")
    return rc, output


def main(apply_bandwidth_throttle=True):

    usage_stats = {
        "user_count": get_user_count(),
        "server_count": get_server_count(),
        "shared_device_count": get_shared_device_count(),
        "data_used_in_month": get_data_used_in_month(),
        "data_used_per_day": get_data_used_per_day(),
    }

    if apply_bandwidth_throttle:
        usage_limits = json.loads(get_usage_limits(EVON_API_URL, EVON_API_KEY))
        mb_used = usage_stats["data_used_in_month"]
        mb_limit = usage_limits.get("max_data_limit_mb")
        throttle_mbps = usage_limits.get("target_throttle_bandwidth_mbps")
        if mb_used >= mb_limit:
            # bandwidth quota has been exceeded, throttle link
            logger.info(f"Bandwidth quota of {mb_limit}MB/month exceeded by {mb_used - mb_limit}MB, throttling to {throttle_mbps}Mbps")
        else:
            # ensure no throttling is applied
            logger.info(f"{mb_limit - mb_used}MB remaining of {mb_limit}MB/month bandwidth quota, ensuring throttles are inactive")
            throttle_mbps = 0

        rc, output = apply_throttle(throttle_mbps)
        if throttle_mbps and not rc:
            usage_stats["bandwidth_throttle_active"] = True
        elif not rc:
            usage_stats["bandwidth_throttle_active"] = False
        else:
            logger.error(f"got non-zero rc {rc} from apply_throttle with output: {output}")

    return usage_stats
