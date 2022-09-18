import os

from django.contrib.auth.models import Group as DjangoGroup
from django.contrib.auth.models import User as DjangoUser
from django.http import FileResponse
from django.http import HttpResponse
from django.shortcuts import render
from drf_spectacular.utils import extend_schema
from rest_access_policy import AccessViewSetMixin
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ViewSet
import requests

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


class ConfigViewSet(ModelViewSet):
    """
    Configuration
    """
    queryset = models.Config.objects.all()
    serializer_class = serializers.ConfigSerializer


class PingViewSet(ViewSet):
    """
    Ping endpoint for connectivity testing
    """
    serializer_class = serializers.PingSerializer

    @extend_schema(
        operation_id="ping_request"
    )
    def list(self, request):
        return Response({"message": "pong"})


class BootstrapViewSet(ViewSet):
    """
    Download the `bootstrap.sh` installer for connecting remote systems to the overlay network hosted by this Hub.
    """
    serializer_class = serializers.BootstrapSerializer

    @extend_schema(
        operation_id="bootstrap_retrieve"
    )
    @action(methods=['get'], detail=False, renderer_classes=(BinaryFileRenderer,))
    def download(self, *args, **kwargs):
        bootstrap_filepath = os.path.join(os.path.realpath(os.path.dirname(__file__)), "..", "bootstrap.sh")
        bootstrap_filename = os.path.basename(bootstrap_filepath)
        f = open(bootstrap_filepath, "rb")
        response = FileResponse(f, content_type='application/octet-stream')
        response['Content-Length'] = os.path.getsize(bootstrap_filepath)
        response['Content-Disposition'] = f'attachment; filename="{bootstrap_filename}"'
        return response


class IIDViewSet(ViewSet):
    """
    Retrieve the Instance Identity Document for the AWS EC2 instance that this Hub is running on.
    """
    serializer_class = serializers.IIDSerializer

    @extend_schema(
        operation_id="iid_retrieve"
    )
    @action(methods=['get'], detail=False)
    def get(self, *args, **kwargs):
        try:
            response = requests.get("http://169.254.169.254/latest/dynamic/instance-identity/document").json()
            status = None
        except requests.exceptions.ConnectionError as e:
            response = {
                "status": "error",
                "message": f"Could not connect to IID URL. You may be running locally rather than on AWS EC2."
            }
            status = "404"
        except Exception as e:
            response = {
                "status": "error",
                "message": f"{e}"
            }
            status = "404"
        return Response(response, status=status)
