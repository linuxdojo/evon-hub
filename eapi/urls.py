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

router.register(r'api/user', hub.views.UserViewSet)
router.register(r'api/group', hub.views.GroupViewSet)
router.register(r'api/server', hub.views.ServerViewSet)
router.register(r'api/servergroup', hub.views.ServerGroupViewSet)
router.register(r'api/policy', hub.views.PolicyViewSet)
router.register(r'api/ping', hub.views.PingViewSet, basename="ping")
router.register(r'api/bootstrap', hub.views.BootstrapViewSet, basename="bootstrap")

urlpatterns = [
    re_path(r'^favicon\.ico$', RedirectView.as_view(permanent=False, url='/static/favicon.ico')),
    path("admin/", admin.site.urls),
    re_path(r'^api/', include('rest_framework.urls', namespace='rest_framework')),
    #re_path(r'^api/$', router.get_api_root_view()),
    re_path(r'^api/$', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    re_path(r'^', include('hub.urls')),
    path('', include(router.urls)),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    #path('api/docs/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
