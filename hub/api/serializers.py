from rest_framework import serializers
from hub import models
from django.contrib.auth.models import User as DjangoUser
from django.contrib.auth.models import Group as DjangoGroup
from rest_access_policy import FieldAccessMixin

from hub.policies import ServerAccessPolicy


class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = DjangoUser
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

    class Meta:
        model = DjangoGroup
        fields = '__all__'


class ServerSerializer(FieldAccessMixin, serializers.ModelSerializer):

    class Meta:
        model = models.Server
        fields = ('id', 'fqdn', 'ipv4_address', 'uuid', 'connected', 'disconnected_since', 'last_seen', 'server_groups')
        access_policy = ServerAccessPolicy


class ServergroupSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.ServerGroup
        fields = '__all__'


class RuleSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.Rule
        fields = '__all__'


class PolicySerializer(serializers.ModelSerializer):

    class Meta:
        model = models.Policy
        fields = '__all__'


class ConfigSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.Config
        fields = ('discovery_mode', 'timezone', 'uuid_blacklist')


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
