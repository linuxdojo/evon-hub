import os

from django.contrib.auth.models import Group as DjangoGroup
from django.contrib.auth.models import User as DjangoUser
from django.http import FileResponse
from django.http import HttpResponse
from django.shortcuts import render
from rest_access_policy import AccessViewSetMixin
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ViewSet

from hub import models
from hub.api import serializers
from hub.permissions import ServerAccessPolicy
from hub.renderers import BinaryFileRenderer

##### App Views ####

def index(request):
    # This view is orphaned in urls in favor of Django Admin
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


class PingViewSet(ViewSet):
    """
    Ping endpoint
    """

    def list(self, request):
        return Response("pong")


class BootstrapViewSet(ViewSet):
    """
    Download bootstrap.sh
    """

    @action(methods=['get'], detail=False, renderer_classes=(BinaryFileRenderer,))
    def download(self, *args, **kwargs):
        bootstrap_filepath = os.path.join(os.path.realpath(os.path.dirname(__file__)), "..", "bootstrap.sh")
        bootstrap_filename = os.path.basename(bootstrap_filepath)
        f = open(bootstrap_filepath, "rb")
        response = FileResponse(f, content_type='application/octet-stream')
        response['Content-Length'] = os.path.getsize(bootstrap_filepath)
        response['Content-Disposition'] = f'attachment; filename="{bootstrap_filename}"'
        return response

