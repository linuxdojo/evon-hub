from rest_framework import serializers
from hub import models
from django.contrib.auth.models import User as DjangoUser
from django.contrib.auth.models import Group as DjangoGroup
from rest_access_policy import FieldAccessMixin

from hub.permissions import ServerAccessPolicy


class UserSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = DjangoUser
        fields = ('id', 'username')


class GroupSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = DjangoGroup
        fields = ('id', 'name')


class ServerSerializer(FieldAccessMixin, serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.Server
        fields = ('id', 'fqdn', 'ipv4_address', 'uuid')
        access_policy = ServerAccessPolicy


class ServergroupSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.ServerGroup
        fields = ('id', 'name')


class PolicySerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.Policy
        fields = ('id', 'name')
