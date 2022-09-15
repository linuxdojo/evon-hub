# Deployment changes in bootstrap

* create superuser (immutable)
* create api user (immutable)
* populate api user token in bootstrap
* run `api collectstatic --noinput` in bootstrap on deploy

# API

* fix errors and warnings re Hello and Server endpoints on runserver start

# Logging

* ensure all django events are logged

# CLI

* add change-deploy-api-key feature to evon cli

# Users

* make superuser and apiuser (deployer?) immutable
