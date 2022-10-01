import os
import socket

from django.contrib.auth.models import Group as DjangoGroup
from django.contrib.auth.models import User as DjangoUser
from django.http import FileResponse
from django.http import HttpResponse
from django.shortcuts import render
from drf_spectacular.utils import extend_schema
from openvpn_status import ParsingError
from rest_access_policy import AccessViewSetMixin
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ViewSet
import requests
#from retry import retry

from eapi.settings import EVON_HUB_CONFIG
from evon import log
from hub import models
from hub import permissions
from hub.api import serializers
from hub.renderers import BinaryFileRenderer


logger = log.get_evon_logger()

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
    access_policy = permissions.ServerAccessPolicy


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


class BootstrapViewSet(AccessViewSetMixin, ViewSet):
    """
    Download the `bootstrap.sh` installer for connecting remote systems to the overlay network hosted by this Hub.
    """
    serializer_class = serializers.BootstrapSerializer
    access_policy = permissions.BootstrapAccessPolicy

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


class OpenVPNMgmtViewSet(AccessViewSetMixin, ViewSet):
    """
    OpenVPN Management Interface
    """
    serializer_class = serializers.OpenVPNMgmtSerializer
    access_policy = permissions.OpenVPNMgmtAccessPolicy

    def __init__(self, *args, **kwargs):
        self.vpn_mgmt_servers = EVON_HUB_CONFIG["vpn_mgmt_servers"]
        self.vpn_mgmt_users = EVON_HUB_CONFIG["vpn_mgmt_users"]
        super().__init__(*args, **kwargs)

    #@retry(ParsingError, tries=5, delay=1)
    @extend_schema(
        operation_id="openvpn_list"
    )
    @action(methods=['get'], detail=False)
    def endpoints(self, *args, **kwargs):
        """
        Obteain a list of connected Servers
        """
        self.vpn_mgmt_servers.connect()
        clients = {k: v.common_name for k, v in self.vpn_mgmt_servers.get_status().routing_table.items()}
        self.vpn_mgmt_servers.disconnect()
        return Response(clients)

    #@retry(ParsingError, tries=5, delay=1)
    @extend_schema(
        operation_id="openvpn_kill"
    )
    @action(methods=['post'], detail=False)
    def kill(self, request, *args, **kwargs):
        """
        Disconnect a Server based on UUID
        """
        if not "uuid" in request.data:
            return Response({"status": "error", "message": "uuid missing in request"}, status="400")
        uuid = request.data["uuid"]
        self.vpn_mgmt_servers.connect()
        result = self.vpn_mgmt_servers.send_command(f"kill {uuid}")
        self.vpn_mgmt_servers.disconnect()
        return Response({"status": "ok", "message": result})
