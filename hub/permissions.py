from rest_access_policy import AccessPolicy


class ServerAccessPolicy(AccessPolicy):
    statements = [
        {
            "action": ["list", "retrieve"],
            "principal": "*",
            "effect": "allow",
            #"condition": "is_authenticated"
        },
        {
            "action": ["*"],
            "principal": ["*"],
            "effect": "allow",
            "condition": "is_superuser"
        },
        {
            "action": ["*"],
            "principal": ["*"],
            "effect": "allow",
            "condition": "is_same_source"
        }
    ]

    def is_same_source(self, request, view, action) -> bool:
        """
        True if requestor_ip_address matches the Server.ipv4_address object in the request
        """
        requestor_ip_addr = request.META['REMOTE_ADDR']
        server_ip_addr = request
        #TODO if requestor_ip_addr == ipv4_addr being updated, return True, else False
        return True

    def is_authenticated(self, request, view, action) -> bool:
        return request.user.is_authenticated

    def is_superuser(self, request, view, action) -> bool:
        return request.user.is_superuser

    @classmethod
    def scope_fields(cls, request, fields: dict, instance=None) -> dict:
        if not request.user.is_superuser:
            fields.pop('uuid', None)
        return fields
