"""eapi URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import re_path, include, path
from django.views.generic.base import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView
from rest_framework import routers

import hub.views


router = routers.DefaultRouter(trailing_slash=False)

#router.register(r'openvpn', hub.views.OpenVPNMgmtViewSet, basename="openvpn")
router.register(r'ping', hub.views.PingViewSet, basename="ping")
router.register(r'bootstrap', hub.views.BootstrapViewSet, basename="bootstrap")
router.register(r'iid', hub.views.IIDViewSet, basename="iid")
router.register(r'ovpnclient', hub.views.OVPNClientViewSet, basename="ovpnclient")

urlpatterns = [
    re_path(r'^favicon\.ico$', RedirectView.as_view(permanent=False, url='/static/favicon.ico')),
    re_path(r'^api/schema', SpectacularAPIView.as_view(), name='schema'),
    re_path(r'^api/$', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('api/', include(router.urls)),
    path('api/permission', hub.views.PermissionListView.as_view()),
    path('api/user', hub.views.UserListView.as_view()),
    path('api/user/<int:pk>', hub.views.UserDetailView.as_view()),
    path('api/group', hub.views.GroupListView.as_view()),
    path('api/group/<int:pk>', hub.views.GroupDetailView.as_view()),
    path('api/server', hub.views.ServerListView.as_view()),
    path('api/server/<int:pk>', hub.views.ServerDetailView.as_view()),
    path('api/servergroup', hub.views.ServerGroupListView.as_view()),
    path('api/servergroup/<int:pk>', hub.views.ServerGroupDetailView.as_view()),
    path('api/config', hub.views.ConfigListView.as_view()),
    path('api/config/<int:pk>', hub.views.ConfigDetailView.as_view()),
    path('api/rule', hub.views.RuleListView.as_view()),
    path('api/rule/<int:pk>', hub.views.RuleDetailView.as_view()),
    path('api/policy', hub.views.PolicyListView.as_view()),
    path('api/policy/<int:pk>', hub.views.PolicyDetailView.as_view()),
    #re_path(r'^', include('hub.urls')),
    re_path("", admin.site.urls),
]
