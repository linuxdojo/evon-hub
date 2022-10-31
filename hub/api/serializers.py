from django.contrib.auth.models import User, Group, Permission
from drf_spectacular.utils import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

import hub.models


class PermissionSerializer(serializers.ModelSerializer):

    class Meta:
        model = Permission
        fields = (
            'id',
            'name',
        )


class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'password',
            'is_superuser',
            'first_name',
            'last_name',
            'email',
            'is_active',
            'groups',
            'user_permissions'
        )


class GroupSerializer(serializers.ModelSerializer):
    user_set = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=User.objects.all(),
        help_text="A list of User ID's that are members of this Group"
    )
    permissions = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Permission.objects.all(),
        help_text="A list of Permission ID's that are granted to members of this group"
    )

    class Meta:
        model = Group
        fields = [
            'name',
            'user_set',
            'permissions',
        ]


class ServerSerializer(serializers.ModelSerializer):
    accessible = serializers.SerializerMethodField(
        read_only=True,
        help_text="This value is set to True only if a policy exists that permits the requesting user to connect to this server."
    )
    last_seen = serializers.SerializerMethodField(
        read_only=True,
        help_text="A human-friendly string describing how long ago the server was last connected to this Hub"
    )

    class Meta:
        model = hub.models.Server
        fields = (
            'id',
            'accessible',
            'fqdn',
            'ipv4_address',
            'uuid',
            'connected',
            'disconnected_since',
            'last_seen',
            'server_groups',
        )

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_accessible(self, server):
        user = None
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            user = request.user 
        return server.user_has_access(user) if user else False

    def get_last_seen(self, server):
        return server.last_seen()


class ServerSerializerRestricted(ServerSerializer):

    class Meta:
        model = hub.models.Server
        fields = (
            'id',
            'fqdn',
            'ipv4_address',
            'connected',
            'disconnected_since',
            'last_seen',
        )


class ServerGroupSerializer(serializers.ModelSerializer):
    server_set = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=hub.models.Server.objects.all()
    )

    class Meta:
        model = hub.models.ServerGroup
        fields = '__all__'


class RuleSerializer(serializers.ModelSerializer):

    class Meta:
        model = hub.models.Rule
        fields = '__all__'


class PolicySerializer(serializers.ModelSerializer):

    class Meta:
        model = hub.models.Policy
        fields = '__all__'


class ConfigSerializer(serializers.ModelSerializer):

    class Meta:
        model = hub.models.Config
        fields = '__all__'


class PingSerializer(serializers.Serializer):
    pass


class BootstrapSerializer(serializers.Serializer):
    pass


class OVPNClientSerializer(serializers.Serializer):
    pass


class IIDSerializer(serializers.Serializer):
    pass


class OpenVPNMgmtSerializer(serializers.Serializer):
    pass
