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
from django.urls import re_path, include, path
from django.contrib import admin
from rest_framework import routers
#from rest_framework_swagger.views import get_swagger_view

import hub.views


#schema_view = get_swagger_view(title='Evon Hub API')

router = routers.DefaultRouter(trailing_slash=False)
router.register(r'api/user', hub.views.UserViewSet)
router.register(r'api/group', hub.views.GroupViewSet)
router.register(r'api/server', hub.views.ServerViewSet)
router.register(r'api/servergroup', hub.views.ServerGroupViewSet)
router.register(r'api/policy', hub.views.PolicyViewSet)
router.register(r'api/hello', hub.views.HelloViewSet, basename="hello")

urlpatterns = [
    path("admin/", admin.site.urls),
    re_path(r'^api/', include('rest_framework.urls', namespace='rest_framework')),
    re_path(r'^api/$', router.get_api_root_view()),
    ##path('api/', include((router.urls, 'app_name'), namespace='instance_name')),
    #re_path(r'^api/$', include((router.urls, "app_name"))),
    re_path(r'^', include('hub.urls')),
    path('', include(router.urls)),
    #re_path(r'^api/docs/', schema_view),
    #path('hub/', include('hub.urls')),
]
