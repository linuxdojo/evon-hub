import hashlib
import ipaddress
import platform
import uuid

import requests


class EC2Metadata:
    def __init__(self):
        self.ipv4_get_urls = [
            "https://ifconfig.me",
            "https://api.ipify.org",
            "https://ipinfo.io/ip",
            "https://ipecho.net/plain",
        ]
        self.metadata = {
            "accountId": "not_applicable",
            "architecture": platform.machine(),
            "availabilityZone": "not_applicable",
            "marketplaceProductCodes": None,
            "instanceId": hashlib.md5(str(uuid.getnode()).encode('utf-8')).hexdigest()[:10],
            "region": "not_applicable",
        }

    def _validate_ipv4(self, ipv4_address):
        try:
            ipaddress.IPv4Address(ipv4_address)
            return True
        except ValueError:
            return False

    def get_metadata_json(self):
        return self.metadata

    def get_pub_ipv4(self):
        for url in self.ipv4_get_urls:
            response = requests.get(url)
            if response.ok and self._validate_ipv4(response.text):
                return response.text
        raise Exception("Failed to obtain public IPv4 address for this system.")

    def get_signature(self):
        return "not_applicable"

    def get_security_credentials(self):
        return "not_applicable"
