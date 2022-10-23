import os
import socket

from django.contrib.auth.models import Group as DjangoGroup
from django.contrib.auth.models import Permission
from django.contrib.auth.models import User as DjangoUser
from django.http import FileResponse
from django.http import HttpResponse
from drf_spectacular.utils import extend_schema, OpenApiTypes, OpenApiExample
from rest_framework import generics
from rest_framework import permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
import requests
#from retry import retry

from eapi.settings import EVON_HUB_CONFIG
from evon import log
from hub import models
from hub.api import serializers
from hub.renderers import BinaryFileRenderer
import hub.permissions


logger = log.get_evon_logger()
EXCLUDED_CONTENT_TYPE_NAMES = EVON_HUB_CONFIG['EXCLUDED_CONTENT_TYPE_NAMES']
EXCLUDED_PERMISSION_NAMES = EVON_HUB_CONFIG['EXCLUDED_PERMISSION_NAMES']


##### App Views ####

def index(request):
    # This view is orphaned in urls in favor of Django Admin
    return HttpResponse("Evon Hub index")


##### API Views ####

class PermissionListView(generics.ListAPIView):
    """
    List all available permissions
    """
    queryset = Permission.objects.exclude(
        content_type__id__in=[p.content_type.id for p in Permission.objects.all() if p.content_type.name in EXCLUDED_CONTENT_TYPE_NAMES]
    ).exclude(
        name__in=EXCLUDED_PERMISSION_NAMES
    ).order_by('id')
    serializer_class = serializers.PermissionSerializer
    permission_classes = (hub.permissions.IsSuperuser,)


class UserListView(generics.ListCreateAPIView):
    """
    List or create Users
    """
    queryset = DjangoUser.objects.all().order_by('id')
    serializer_class = serializers.UserSerializer
    permission_classes = (hub.permissions.HubDjangoModelPermissions,)


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a User
    """
    queryset = DjangoUser.objects.all()
    serializer_class = serializers.UserSerializer
    permission_classes = (hub.permissions.HubDjangoModelPermissions,)
    http_method_names = ['get', 'post', 'patch', 'delete']


class GroupListView(generics.ListCreateAPIView):
    """
    List or create Groups
    """
    queryset = DjangoGroup.objects.all().order_by('id')
    serializer_class = serializers.GroupSerializer
    permission_classes = (hub.permissions.HubDjangoModelPermissions,)


class GroupDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a Group
    """
    queryset = DjangoGroup.objects.all()
    serializer_class = serializers.GroupSerializer
    permission_classes = (hub.permissions.HubDjangoModelPermissions,)
    http_method_names = ['get', 'post', 'patch', 'delete']


class ServerListView(generics.ListAPIView):
    """
    List Servers
    """
    queryset = models.Server.objects.all().order_by('id')
    serializer_class = serializers.ServerSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        if self.request.user.is_superuser:
            return models.Server.objects.all().order_by('id')
        allowed_servers = [s.pk for s in models.Server.objects.all() if s.user_has_access(self.request.user)]
        return models.Server.objects.filter(pk__in=allowed_servers).order_by('id')

    def get_serializer_class(self):
        if self.request.user.is_superuser:
            return serializers.ServerSerializer
        else:
            return serializers.ServerSerializerRestricted


class ServerDetailView(generics.RetrieveAPIView, generics.UpdateAPIView, generics.DestroyAPIView):
    """
    Retrieve, update or delete a Server
    """
    queryset = models.Server.objects.all().order_by('id')
    serializer_class = serializers.ServerSerializer
    permission_classes = (hub.permissions.HubDjangoModelPermissions,)
    http_method_names = ['get', 'post', 'patch', 'delete']


class ServerGroupListView(generics.ListCreateAPIView):
    """
    List or create Server Group
    """
    queryset = models.ServerGroup.objects.all().order_by('id')
    serializer_class = serializers.ServerGroupSerializer
    permission_classes = (hub.permissions.HubDjangoModelPermissions,)


class ServerGroupDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a Server Group
    """
    queryset = models.ServerGroup.objects.all().order_by('id')
    serializer_class = serializers.ServerGroupSerializer
    permission_classes = (hub.permissions.HubDjangoModelPermissions,)
    http_method_names = ['get', 'post', 'patch', 'delete']


class ConfigListView(generics.ListAPIView):
    """
    List Config
    """
    queryset = models.Config.objects.all().order_by('id')
    serializer_class = serializers.ConfigSerializer
    permission_classes = (hub.permissions.HubDjangoModelPermissions,)


class ConfigDetailView(generics.UpdateAPIView):
    """
    Retrieve or update Config
    """
    queryset = models.Config.objects.all().order_by('id')
    serializer_class = serializers.ConfigSerializer
    permission_classes = (hub.permissions.HubDjangoModelPermissions,)
    http_method_names = ['patch']


class RuleListView(generics.ListCreateAPIView):
    """
    List or create Rules 
    """
    queryset = models.Rule.objects.all().order_by("id")
    serializer_class = serializers.RuleSerializer
    permission_classes = (hub.permissions.HubDjangoModelPermissions,)


class RuleDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a Rule
    """
    queryset = models.Rule.objects.all().order_by('id')
    serializer_class = serializers.RuleSerializer
    permission_classes = (hub.permissions.HubDjangoModelPermissions,)
    http_method_names = ['get', 'post', 'patch', 'delete']


class PolicyListView(generics.ListCreateAPIView):
    """
    List or create Policies
    """
    queryset = models.Policy.objects.all().order_by("id")
    serializer_class = serializers.PolicySerializer
    permission_classes = (hub.permissions.HubDjangoModelPermissions,)


class PolicyDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a Policy
    """
    queryset = models.Policy.objects.all().order_by('id')
    serializer_class = serializers.PolicySerializer
    permission_classes = (hub.permissions.HubDjangoModelPermissions,)
    http_method_names = ['get', 'post', 'patch', 'delete']


class PingViewSet(ViewSet):
    """
    Ping endpoint for availability/connectivity testing of Evon Hub API
    """
    serializer_class = serializers.PingSerializer
    permission_classes = (permissions.IsAuthenticated,)

    @extend_schema(
        operation_id="ping_request",
        responses={
            200: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                'example response',
                description='Successful response',
                value={
                    'message': 'pong',
                },
                response_only=True,
            ),
        ]
    )
    def list(self, request):
        return Response({"message": "pong"})


class BootstrapViewSet(ViewSet):
    """
    Download the `bootstrap.sh` installer for connecting remote systems to this overlay network.
    Requesting user must be a superuser or the "depoloyer" user.
    """
    serializer_class = serializers.BootstrapSerializer
    permission_classes = (hub.permissions.IsSuperuserOrDeployer,)

    @extend_schema(
        operation_id="bootstrap_retrieve",
        responses={
            (200, 'application/octet-stream'): OpenApiTypes.BINARY
        }
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


class OVPNClientViewSet(ViewSet):
    """
    Download the `EvonHub.ovpn` OpenVPN configuration file for user access to this overlay network.
    """
    serializer_class = serializers.OVPNClientSerializer
    permission_classes = (permissions.IsAuthenticated,)

    @extend_schema(
        operation_id="ovpnclient_retrieve",
        responses={
            (200, 'application/octet-stream'): OpenApiTypes.BINARY
        }
    )
    @action(methods=['get'], detail=False, renderer_classes=(BinaryFileRenderer,))
    def download(self, *args, **kwargs):
        ovpnclient_filepath = os.path.join(os.path.realpath(os.path.dirname(__file__)), "..", "EvonHub.ovpn")
        ovpnclient_filename = os.path.basename(ovpnclient_filepath)
        f = open(ovpnclient_filepath, "rb")
        response = FileResponse(f, content_type='application/octet-stream')
        response['Content-Length'] = os.path.getsize(ovpnclient_filepath)
        response['Content-Disposition'] = f'attachment; filename="{ovpnclient_filename}"'
        return response


#class OpenVPNMgmtViewSet(ViewSet):
#    """
#    OpenVPN Management Interface
#    """
#    serializer_class = serializers.OpenVPNMgmtSerializer
#    permission_classes = (hub.permissions.IsSuperuser,)
#
#    def __init__(self, *args, **kwargs):
#        self.vpn_mgmt_servers = EVON_HUB_CONFIG["vpn_mgmt_servers"]
#        self.vpn_mgmt_users = EVON_HUB_CONFIG["vpn_mgmt_users"]
#        super().__init__(*args, **kwargs)
#
#    @extend_schema(
#        operation_id="openvpn_list"
#    )
#    @action(methods=['get'], detail=False)
#    def endpoints(self, *args, **kwargs):
#        """
#        Retrieve a list of OpenVPN connected Servers on this hub.
#        Requesting user must be a superuser.
#        """
#        self.vpn_mgmt_servers.connect()
#        clients = {k: v.common_name for k, v in self.vpn_mgmt_servers.get_status().routing_table.items()}
#        self.vpn_mgmt_servers.disconnect()
#        return Response(clients)
#
#    @extend_schema(
#        operation_id="openvpn_kill"
#    )
#    @action(methods=['post'], detail=False)
#    def kill(self, request, *args, **kwargs):
#        """
#        Disconnect a Server based on UUID.
#        Requesting user must be a superuser.
#        """
#        if not "uuid" in request.data:
#            return Response({"status": "error", "message": "uuid missing in request"}, status="400")
#        uuid = request.data["uuid"]
#        self.vpn_mgmt_servers.connect()
#        result = self.vpn_mgmt_servers.send_command(f"kill {uuid}")
#        self.vpn_mgmt_servers.disconnect()
#        return Response({"status": "ok", "message": result})


class IIDViewSet(ViewSet):
    """
    Retrieve the Instance Identity Document for the AWS EC2 instance that this Hub is running on.
    """
    serializer_class = serializers.IIDSerializer
    permission_classes = (hub.permissions.IsSuperuserOrDeployer,)

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
