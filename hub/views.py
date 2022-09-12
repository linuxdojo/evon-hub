from django.http import HttpResponse
from django.shortcuts import render
from django.contrib.auth.models import User as DjangoUser
from django.contrib.auth.models import Group as DjangoGroup
from hub import models
from hub.api import serializers
from rest_framework import viewsets, permissions
from rest_framework.response import Response

from hub.permissions import PermissionPolicyMixin

##### App Views ####

def index(request):
    # TODO redirect this to an external index in /var/www/html
    return HttpResponse("Evon Hub index")


##### API Views ####

class UserViewSet(viewsets.ModelViewSet):
    """
    Users
    """
    queryset = DjangoUser.objects.all()
    serializer_class = serializers.UserSerializer


class GroupViewSet(viewsets.ModelViewSet):
    """
    Groups
    """
    queryset = DjangoGroup.objects.all()
    serializer_class = serializers.GroupSerializer


class ServerViewSet(PermissionPolicyMixin, viewsets.ModelViewSet):
    """
    Servers
    """
    queryset = models.Server.objects.all()
    serializer_class = serializers.ServerSerializer
    permission_classes = [permissions.IsAdminUser]
    permission_classes_per_method = {
        "list": [permissions.IsAdminUser | permissions.IsAuthenticated],
        "retrieve": [permissions.IsAdminUser | permissions.IsAuthenticated]
    }



class ServerGroupViewSet(viewsets.ModelViewSet):
    """
    Server Groups
    """
    queryset = models.ServerGroup.objects.all()
    serializer_class = serializers.ServergroupSerializer


class PolicyViewSet(viewsets.ModelViewSet):
    """
    Permissions policies
    """
    queryset = models.Policy.objects.all()
    serializer_class = serializers.PolicySerializer


class HelloViewSet(viewsets.ViewSet):
    """
    Custom hello endpoint
    """
    def list(self, response):
        return Response("hello world")
