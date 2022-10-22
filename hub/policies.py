from rest_access_policy import AccessPolicy


class ServerAccessPolicy(AccessPolicy):
    statements = [
        {
            "action": ["list", "retrieve"],
            "principal": "*",
            "effect": "allow",
            "condition": "is_authenticated"
        },
        {
            "action": ["*"],
            "principal": ["*"],
            "effect": "allow",
            "condition": "is_superuser"
        },
    ]

    def is_authenticated(self, request, view, action) -> bool:
        return request.user.is_authenticated

    def is_superuser(self, request, view, action) -> bool:
        return request.user.is_superuser

    @classmethod
    def scope_fields(cls, request, fields: dict, instance=None) -> dict:
        if not request.user.is_superuser:
            fields.pop('uuid', None)
            fields.pop('server_groups', None)
        return fields


class OpenVPNMgmtAccessPolicy(AccessPolicy):
    statements = [
        {
            "action": ["*"],
            "principal": ["*"],
            "effect": "allow",
            "condition": "is_superuser"
        },
    ]

    def is_superuser(self, request, view, action) -> bool:
        return request.user.is_superuser


class ConfigAccessPolicy(AccessPolicy):
    statements = [
        {
            "action": ["*"],
            "principal": ["*"],
            "effect": "allow",
            "condition": "is_superuser"
        },
    ]

    def is_superuser(self, request, view, action) -> bool:
        return request.user.is_superuser


class BootstrapAccessPolicy(AccessPolicy):
    statements = [
        {
            "action": ["*"],
            "principal": ["*"],
            "effect": "allow",
            "condition": "is_deployer"
        },
    ]

    def is_deployer(self, request, view, action) -> bool:
        return request.user.username in ["admin", "deployer"]


class OVPNClientAccessPolicy(AccessPolicy):
    statements = [
        {
            "action": ["*"],
            "principal": ["*"],
            "effect": "allow",
            "condition": "is_authenticated"
        },
    ]

    def is_authenticated(self, request, view, action) -> bool:
        return request.user.is_authenticated
