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

router.register(r'user', hub.views.UserViewSet)
router.register(r'group', hub.views.GroupViewSet)
router.register(r'server', hub.views.ServerViewSet)
router.register(r'servergroup', hub.views.ServerGroupViewSet)
router.register(r'policy', hub.views.PolicyViewSet)
router.register(r'config', hub.views.ConfigViewSet)
router.register(r'ping', hub.views.PingViewSet, basename="ping")
router.register(r'bootstrap', hub.views.BootstrapViewSet, basename="bootstrap")
router.register(r'iid', hub.views.IIDViewSet, basename="iid")
router.register(r'openvpn', hub.views.OpenVPNMgmtViewSet, basename="openvpn")

urlpatterns = [
    re_path(r'^favicon\.ico$', RedirectView.as_view(permanent=False, url='/static/favicon.ico')),
    #re_path(r'^api/', include('rest_framework.urls', namespace='rest_framework')),
    re_path(r'^api/schema', SpectacularAPIView.as_view(), name='schema'),
    re_path(r'^api/$', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('api/', include(router.urls)),
    #path("admin/", admin.site.urls),
    #re_path(r'^', include('hub.urls')),
    re_path("", admin.site.urls),
]
