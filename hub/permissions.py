from rest_framework.permissions import DjangoModelPermissions, BasePermission


class HubDjangoModelPermissions(DjangoModelPermissions):
    perms_map = {
        'GET':['%(app_label)s.view_%(model_name)s'],
        'OPTIONS': [],
        'HEAD': [],
        'POST': ['%(app_label)s.add_%(model_name)s'],
        'PUT': ['%(app_label)s.change_%(model_name)s'],
        'PATCH': ['%(app_label)s.change_%(model_name)s'],
        'DELETE': ['%(app_label)s.delete_%(model_name)s'],
    }


class IsSuperuser(BasePermission):
    """
    Superuser permission check
    """

    def has_permission(self, request, view):
        return request.user.is_superuser


class IsSuperuserOrDeployer(BasePermission):
    """
    Superuser or deployer permission check
    """

    def has_permission(self, request, view):
        return request.user.is_superuser or request.user.username == "deployer"
