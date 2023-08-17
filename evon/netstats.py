#!/usr/bin/env python

from collections import defaultdict
import datetime
import os
import json
import subprocess

import django
os.environ['DJANGO_SETTINGS_MODULE'] = 'eapi.settings'  # noqa
django.setup()  # noqa

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
    Returns current server count (servers + shared user devices) on the hub
    """
    return Server.objects.count() + UserProfile.objects.filter(shared=True).count()


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


def commit_stats(user_count, server_count, data_used_in_month, data_used_per_day):
    payload = {
        "user_count": user_count,
        "server_count": server_count,
        "data_used_in_month": data_used_in_month,
        "data_used_per_day": data_used_per_day,
    }
    return payload


def main():
    return commit_stats(
        get_user_count(),
        get_server_count(),
        get_data_used_in_month(),
        get_data_used_per_day(),
    )
