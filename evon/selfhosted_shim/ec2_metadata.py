import platform
import re
from os.path import isfile

import requests


class EC2Metadata:

    def __init__(self):
        self.ipv4_get_urls = [
            "https://api.ipify.org"
            "https://ifconfig.me",
        ]
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
        try:
            with open(self.hwaddr_path, "r") as f:
                hwaddr = f.read().strip()
                if not self.hwaddr_patt.match(hwaddr):
                    raise Exception("hwaddr pattern mismatch")
        except FileNotFoundError:
            # set arbitrary hwaddr for local dev
            hwaddr = "selfhosted-0000000000"
        return hwaddr

    def get_metadata_json(self):
        return self.metadata

    def get_pub_ipv4(self):
        if isfile(self.static_pub_ipv4_path):
            with open(self.static_pub_ipv4_path, "r") as f:
                pub_ipv4 = f.read().strip()
            if self.non_rfc1918_ip_patt.match(pub_ipv4):
                # XXX this can be abused as a malicious selfhosted customer may point their hub A record to any pub address...
                return pub_ipv4
            else:
                raise Exception(f"File '{self.static_pub_ipv4_path}' does not contain a valid public ip address.")
        else:
            for url in self.ipv4_get_urls:
                response = requests.get(url)
                if response.ok and self.non_rfc1918_ip_patt.match(response.text):
                    return response.text
            raise Exception("Failed to automatically obtain this system's public IPv4 address.")

    def get_signature(self):
        return "not-applicable"

    def get_security_credentials(self):
        return "not-applicable"
