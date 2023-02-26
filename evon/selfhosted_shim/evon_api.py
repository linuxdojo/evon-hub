import os


# TODO make root_domain configurable somewhere...
API_ROOT_DOMAIN = os.environ.get('API_ROOT_DOMAIN', "example.com")


class EvonAPI:
    def __init__(self, root_domain=API_ROOT_DOMAIN):
        self.root_domain = root_domain

    def get_update(self):
        return {
            "update_available": False,
            "status": "success"
        }

    def register(self, data):
        return {
            "account_domain": f"{data['domain_prefix']}.{self.root_domain}",
            "subnet_key": data["subnet_key"],
            "message": "success"
        }

    def deregister(self, data):
        pub_ipv4 = data["public-ipv4"]
        subnet_key = pub_ipv4.split(".")[1]
        account_domain = f"{data['domain-prefix']}.{self.root_domain}",
        return {
            "account_domain": account_domain,
            "subnet_key": subnet_key,
            "public_ipv4": pub_ipv4,
            "message": "account successfully deregistered"
        }

    def get_records(self):
        return {"message": "not implemented"}

    def set_records(self, changes):
        # TODO - imoplement an example route53 updater for this method
        return {"message": "not implemented"}
