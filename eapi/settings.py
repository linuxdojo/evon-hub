"""
Django settings for eapi project.

Generated by 'django-admin startproject' using Django 4.1.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.1/ref/settings/
"""

import os

from openvpn_api.vpn import VPN
from pathlib import Path
import psutil
import yaml


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_PATH = os.path.realpath(os.path.dirname(__file__))
with open(os.path.join(f"{BASE_DIR}", "version.txt")) as verfile:
    VERSION = verfile.read().strip()

def join_paths(*args):
    return os.path.join(*args) + os.path.sep


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-p2yq#!5zo1ok+sg5bt)_21llif+#-kjrhmrn)z2byap%8*8-ui"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = [
    ".evon.link",
    "localhost",
]


# Application definition

INSTALLED_APPS = [
    "hub.apps.HubConfig",
    "jazzmin",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "drf_spectacular",
    #"auditlog",
    "hub.apps.HubAuditLogConfig",
]

EVON_HUB_CONFIG = {
    "vpn_mgmt_servers": VPN(unix_socket="/etc/openvpn/evon_mgmt_servers"),
    "vpn_mgmt_users": VPN(unix_socket="/etc/openvpn/evon_mgmt_users"),
}

with open(os.path.join(BASE_DIR, "evon_vars.yaml")) as f:
    EVON_VARS = yaml.safe_load(f)

JAZZMIN_SETTINGS = {
    "site_title": "Evon Hub",
    "site_header": "Evon Hub Admin",
    "site_brand": f"Evon Hub {VERSION}",
    "welcome_sign": "Evon Hub",
    "site_logo": "evon_logo_e.png",
    "site_icon": "favicon.ico",
    "copyright": "LinuxDojo.com",
    #"related_modal_active": True,
    "order_with_respect_to": [
        "auth",
        "auth.user",
        "auth.group",
        "authtoken",
        "hub",
        "hub.config",
        "hub.server",
        "hub.servergroup",
        "hub.policy",
        "hub.bootstrap",
        "hub.ovpnclientconfig",
        "auditlog",
    ],
    "topmenu_links": [
        {"name": "View API Documentation", "url": "/api", "new_window": True},
    ],
    "icons": {
        "auditlog.logentry": "fas fa-list-alt",
        "authtoken.tokenproxy": "fas fa-key",
        "auth.group": "fas fa-users",
        "auth.user": "fas fa-user",
        "hub.policy": "fas fa-shield-alt",
        "hub.server": "fas fa-server",
        "hub.config": "fas fa-cog",
        "hub.servergroup": "fas fa-network-wired",
        "hub.bootstrap": "fas fa-download",
        "hub.ovpnclientconfig": "fas fa-laptop-code",
    },
}

JAZZMIN_UI_TWEAKS = {
    "theme": "flatly",
    "dark_mode_theme": "darkly",
}


AUDITLOG_INCLUDE_ALL_MODELS = True

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "auditlog.middleware.AuditlogMiddleware",
]

ROOT_URLCONF = "eapi.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
            "libraries": {
                "staticfiles": "django.templatetags.static",
            },
        },
    },
]

WSGI_APPLICATION = "eapi.wsgi.application"


# Database
# https://docs.djangoproject.com/en/4.1/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        'NAME': 'evon',
        'USER': 'evon',
        'PASSWORD': 'evon',
        'HOST': 'localhost',
        'PORT': '3306',
    }
}


# Password validation
# https://docs.djangoproject.com/en/4.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)

# https://docs.djangoproject.com/en/4.1/howto/static-files/
# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/var/www/example.com/static/"
STATIC_ROOT = join_paths(PROJECT_PATH, 'static')

STATIC_URL = "static/"

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)


# Default primary key field type
# https://docs.djangoproject.com/en/4.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Rest Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
        #'rest_framework.permissions.IsAdminUser',
        #'rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly',
        #'rest_framework.permissions.AllowAny',
    ],
    #'DEFAULT_SCHEMA_CLASS': 'rest_framework.schemas.coreapi.AutoSchema',
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100,
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Evon Hub API',
    'DESCRIPTION': """`[ Elastic Virtual Overlay Network ]`\n
Evon Hub API Documentation.\n
    """,
    'VERSION': VERSION,
    'SERVE_INCLUDE_SCHEMA': True,
    # OTHER SETTINGS
}
