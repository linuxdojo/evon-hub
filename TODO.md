# MVP Release

## Hub Installer package

* implement s3 publishing and upgrading process

## OpenVPN

* add an auth script for UDP that checks against a dango user

## Policy

* implement

## Miscelaneous

* setup support@evon.link email and add to cli and web admin, setup webpage on linuxdojo.com
* publish on AWSMP, indicate that inbound tcp/443, tcp/80, udp/1194 are required
* address TODO, FIXME, XXX comments
* default admin password is ec2 id. Force change first login.
* in bootstrap, send enc payload to hub for decrypt, with optional local decrypt (use same EVON_DEPLOY_KEY for both, try local decrypt, then remote).
* consider redirecting all hub urls to django app in nginx. SSL certs and ALLOWED_HOSTS needs to be managed accordingly. Alternate/simpler: allow clients to choose their own domain prefix rather than the 5 character auto-generated one.
