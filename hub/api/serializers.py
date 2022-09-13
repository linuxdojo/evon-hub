from rest_framework import serializers
from hub import models
from django.contrib.auth.models import User as DjangoUser
from django.contrib.auth.models import Group as DjangoGroup
from rest_access_policy import FieldAccessMixin

from hub.permissions import ServerAccessPolicy


class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = DjangoUser
        fields = ('id', 'username')


class GroupSerializer(serializers.ModelSerializer):

    class Meta:
        model = DjangoGroup
        fields = ('id', 'name')


class ServerSerializer(FieldAccessMixin, serializers.ModelSerializer):

    class Meta:
        model = models.Server
        fields = ('id', 'fqdn', 'ipv4_address', 'uuid')
        access_policy = ServerAccessPolicy


class ServergroupSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.ServerGroup
        fields = ('id', 'name')


class PolicySerializer(serializers.ModelSerializer):

    class Meta:
        model = models.Policy
        fields = ('id', 'name')
