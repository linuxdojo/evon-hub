#!/bin/bash

# run this script to setup django db for local dev using dev server (eapi runserver)

cat <<EOF | eapi shell
from django.contrib.auth import get_user_model
import json
import requests
from hub import models
User = get_user_model()  
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', '', 'admin')
if not User.objects.filter(username='deployer').exists():
    User.objects.create_user('deployer', '', '')
models.Config.get_solo()
EOF
