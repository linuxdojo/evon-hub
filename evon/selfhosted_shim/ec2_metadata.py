import logging
import platform
import random
import re
from os.path import isfile

import requests
logger = logging.getLogger("uvicorn")


class EC2Metadata:

    def __init__(self):
        self.ipv4_get_urls = [
            "https://api.ipify.org",
            "https://ifconfig.me",
            "https://ident.me",
            "https://ipinfo.io/ip",
            "https://ipecho.net/plain",
            "https://www.trackip.net/ip"
        ]
        self.ipv4_get_timeout = 3
        self.non_rfc1918_ip_patt = re.compile(r"\b(?!10\.|192\.168\.|172\.(?:1[6-9]|2[0-9]|3[01])\.)(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(?:\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)){3}\b")
        self.static_pub_ipv4_path = "/opt/.evon-hub.static_pub_ipv4"
        self.hwaddr_patt = re.compile(r"^[a-zA-Z0-9]{10}$")
        self.hwaddr_path = "/opt/.evon-hub.hwaddr"
        hardware_address = self.get_hwaddr()
        self.metadata = {
            "accountId": f"selfhosted-{hardware_address}",
            "architecture": platform.machine(),
            "availabilityZone": "selfhosted",
            "marketplaceProductCodes": None,
            "instanceId": hardware_address,
            "region": "selfhosted",
        }

    def get_hwaddr(self):
        default_hwaddr = "selfhosted-0000000000"
        try:
            with open(self.hwaddr_path, "r") as f:
                hwaddr = f.read().strip()
                if not self.hwaddr_patt.match(hwaddr):
                    logger.warning(f"file '{self.hwaddr_path}' does not contain a valid hardware address, returning default hwaddr: {default_hwaddr}")
                    hwaddr = default_hwaddr
        except FileNotFoundError:
            # set arbitrary hwaddr for local dev
            logger.warning(f"file '{self.hwaddr_path}' not found, returning default hwaddr: {default_hwaddr}")
            hwaddr = default_hwaddr
        return hwaddr

    def get_metadata_json(self):
        return self.metadata

    def get_pub_ipv4(self):
        # set a default incase we can't derive
        default_pub_ipv4 = "0.0.0.0"
        if isfile(self.static_pub_ipv4_path):
            with open(self.static_pub_ipv4_path, "r") as f:
                pub_ipv4 = f.read().strip()
            if self.non_rfc1918_ip_patt.match(pub_ipv4):
                return pub_ipv4
            else:
                logger.error(f"file '{self.static_pub_ipv4_path}' does not contain a valid public ip address, returning default: {default_pub_ipv4}")
                return default_pub_ipv4
        else:
            urls = self.ipv4_get_urls[:]
            random.shuffle(urls)
            for url in urls:
                logger.info(f"trying to obtain pub ipv4 from: {url}")
                response = requests.get(url, timeout=self.ipv4_get_timeout)
                pub_ipv4 = response.text.strip()
                if response.ok and self.non_rfc1918_ip_patt.match(pub_ipv4):
                    logger.info(f"obtained pub ipv4: {pub_ipv4}")
                    return pub_ipv4
                logger.warning(f"failed to obtain pub ipv4 from: {pub_ipv4}")
            logger.error(f"failed to automatically obtain this system's public IPv4 address, returning default: {default_pub_ipv4}")
            return default_pub_ipv4

    def get_signature(self):
        return "not-applicable"

    def get_security_credentials(self):
        return "not-applicable"
