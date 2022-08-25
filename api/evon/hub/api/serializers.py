from rest_framework import serializers
from hub import models


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.User
        fields = ('user_name')


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Group
        fields = ('group_name')


class ServerSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Server
        fields = ('fqdn', 'ipv4_address')


class ServergroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Servergroup
        fields = ('servergroup_name')


class PolicySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Policy
        fields = ('policy_name')
