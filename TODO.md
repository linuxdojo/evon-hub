# MVP Release

## Hub Installer package

* implement s3 publishing and upgrading process

## API

* validate api permissions

## Miscelaneous

* pages for 500, 404 and 404 (when deleting admin/deployer users from signals)
* add get syslog logs to api endpoints
* setup support@evon.link email and add to cli and web admin, setup webpage on linuxdojo.com
* publish on AWSMP, indicate that inbound tcp/443, tcp/80, udp/1194 are required
* address TODO, FIXME, XXX
* create a new persisted secret key in settings.py when deploying, see https://saasitive.com/tutorial/generate-django-secret-key/
* add option to set hostname in bootstrap invocation (rather than `uname -n` default) and expose UUID and HOSTNAME via env var options in bootstrap docker

# Future Release

* replace evon cli and its sudo wrappers in /usr/local/bin with eapi manage commands
* add tooltips top Admin group objects to show members at a glance
* rename policy.servergroups to policy.target_server_groups and policy.servers to policy.target_servers
* add a connected bool field to UserProfile and show in admin User list
* documentation (readthedocs/sphinx style)
* consider redirecting all hub urls to django app in nginx. SSL certs and ALLOWED_HOSTS needs to be managed accordingly. Alternate/simpler: allow clients to choose their own domain prefix rather than the 5 character auto-generated one.
* default admin password is ec2 id. Force change first login.
* in bootstrap, send enc payload to hub for decrypt, with optional local decrypt (use same EVON_DEPLOY_KEY for both, try local decrypt, then remote).
* add mfa (consider django-mfa2 or django-mfa3)
