import os


# TODO make root_domain settable
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
        return {"message": "not implemented"}

    def get_records(self):
        return {"message": "not implemented"}

    def set_records(self, changes):
        # TODO
        return {"message": "not implemented"}
