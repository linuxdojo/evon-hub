from rest_framework import permissions


class PermissionPolicyMixin:
    """
    See https://b0uh.github.io/drf-viewset-permission-policy-per-method.html
    """
    def check_permissions(self, request):
        try:
            # This line is heavily inspired from `APIView.dispatch`.
            # It returns the method associated with an endpoint.
            handler = getattr(self, request.method.lower())
        except AttributeError:
            handler = None

        if (
            handler
            and self.permission_classes_per_method
            and self.permission_classes_per_method.get(handler.__name__)
        ):
            self.permission_classes = self.permission_classes_per_method.get(handler.__name__)

        super().check_permissions(request)


class SameSourcePermission(permissions.BasePermission):
    """
    Ensures endpoints can only modify their own records
    """

    def has_permission(self, request, view):
        requestor_ip_addr = request.META['REMOTE_ADDR']
        #TODO if requestor_ip_addr == ipv4_addr being updated, return True, else False
