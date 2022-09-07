from rest_framework import serializers
from hub import models
from django.contrib.auth.models import User as DjangoUser
from django.contrib.auth.models import Group as DjangoGroup


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = DjangoUser
        fields = ('username',)


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = DjangoGroup
        fields = ('name',)


class ServerSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Server
        fields = ('fqdn', 'ipv4_address')


class ServergroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Servergroup
        fields = ('servergroup_name',)


class PolicySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Policy
        fields = ('policy_name',)
