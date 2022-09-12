from django.contrib.auth.models import Group as DjangoGroup
from django.contrib.auth.models import User as DjangoUser
from django.http import HttpResponse
from django.shortcuts import render
from rest_access_policy import AccessViewSetMixin
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ViewSet

from hub import models
from hub.api import serializers
from hub.permissions import ServerAccessPolicy

##### App Views ####

def index(request):
    # TODO redirect this to an external index in /var/www/html
    return HttpResponse("Evon Hub index")


##### API Views ####

class UserViewSet(ModelViewSet):
    """
    Users
    """
    queryset = DjangoUser.objects.all()
    serializer_class = serializers.UserSerializer


class GroupViewSet(ModelViewSet):
    """
    Groups
    """
    queryset = DjangoGroup.objects.all()
    serializer_class = serializers.GroupSerializer


class ServerViewSet(AccessViewSetMixin, ModelViewSet):
    """
    Servers
    """
    queryset = models.Server.objects.all()
    serializer_class = serializers.ServerSerializer
    access_policy = ServerAccessPolicy


class ServerGroupViewSet(ModelViewSet):
    """
    Server Groups
    """
    queryset = models.ServerGroup.objects.all()
    serializer_class = serializers.ServergroupSerializer


class PolicyViewSet(ModelViewSet):
    """
    Permissions policies
    """
    queryset = models.Policy.objects.all()
    serializer_class = serializers.PolicySerializer


class HelloViewSet(ViewSet):
    """
    Custom hello endpoint
    """
    def list(self, response):
        return Response("hello world")
