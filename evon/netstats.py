#!/usr/bin/env python

import psutil

# Must run as root

def get_interfaces():
    """
    returns a list of non-loopback interfaces that are up
    """
    addresses = psutil.net_if_addrs()
    stats = psutil.net_if_stats()
    interfaces = []
    for interface, addr_list in addresses.items():
        if any(getattr(addr, 'address').startswith("169.254") for addr in addr_list):
            continue
        elif interface in stats \
            and getattr(stats[interface], "isup") \
            and "loopback" not in getattr(stats[interface], 'flags'):
            interfaces.append(interface)
    return interfaces


# TODO use vnstat to collect 5-minutely, daily and monthly TX data counts

if __name__ == "__main__":
    interfaces = get_interfaces()
    print(interfaces)
