from django.shortcuts import render
from django.http import HttpResponse
from rest_framework import viewsets
from hub import models
from hub.api import serializers


##### App Views ####

def index(request):
    return HttpResponse("Evon Hub index")


##### API Views ####

class UserViewSet(viewsets.ModelViewSet):
    queryset = models.User.objects.all()
    serializer_class = serializers.UserSerializer


class GroupViewSet(viewsets.ModelViewSet):
    queryset = models.Group.objects.all()
    serializer_class = serializers.GroupSerializer


class ServerViewSet(viewsets.ModelViewSet):
    queryset = models.Server.objects.all()
    serializer_class = serializers.ServerSerializer


class ServergroupViewSet(viewsets.ModelViewSet):
    queryset = models.Servergroup.objects.all()
    serializer_class = serializers.ServergroupSerializer


class PolicyViewSet(viewsets.ModelViewSet):
    queryset = models.Policy.objects.all()
    serializer_class = serializers.PolicySerializer
