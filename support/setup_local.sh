#!/bin/bash

# run this script to setup django db for local dev using dev server (eapi runserver)
#
pip install -r requirements.txt
pip install -r requirements-test.txt
pip install -e .

cat <<EOF | eapi shell
from django.contrib.auth import get_user_model
from hub import models
User = get_user_model()  
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', '', 'admin')
if not User.objects.filter(username='deployer').exists():
    User.objects.create_user('deployer', '', '')
models.Config.get_solo()
EOF
