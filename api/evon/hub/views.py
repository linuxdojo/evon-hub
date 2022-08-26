from django.http import HttpResponse
from django.shortcuts import render
from hub import models
from hub.api import serializers
from rest_framework import viewsets
from rest_framework.response import Response


##### App Views ####

def index(request):
    return HttpResponse("Evon Hub index")


##### API Views ####

class UserViewSet(viewsets.ModelViewSet):
    """
    Evon users
    """
    queryset = models.User.objects.all()
    serializer_class = serializers.UserSerializer


class GroupViewSet(viewsets.ModelViewSet):
    """
    Evon user groups
    """
    queryset = models.Group.objects.all()
    serializer_class = serializers.GroupSerializer


class ServerViewSet(viewsets.ModelViewSet):
    """
    Evon connected servers
    """
    queryset = models.Server.objects.all()
    serializer_class = serializers.ServerSerializer


class ServergroupViewSet(viewsets.ModelViewSet):
    """
    Evon server groups
    """
    queryset = models.Servergroup.objects.all()
    serializer_class = serializers.ServergroupSerializer


class PolicyViewSet(viewsets.ModelViewSet):
    """
    Evon permissions policies
    """
    queryset = models.Policy.objects.all()
    serializer_class = serializers.PolicySerializer

class HelloViewSet(viewsets.ViewSet):
    """
    Custom hello endpoint
    """
    def list(self, response):
        return Response("hello world")
