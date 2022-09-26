# MVP Release

## Hub Installer package

* implement s3 publishing and upgrading process

## OpenVPN

* ✅ create auth-user-pass-verify script for `evon-hub/templates/openvpn/server/server_tcp.conf`
 * ❌ check for duplicate (currently connected) uuid and reject if so (blocked: ovpn mgmt interface hangs during auth exec)
 * ✅ consider discovery|operational modes via custom login scripts for server acquisition vs. changeless op mode
* ✅ on Evon Hub service start: sync all connected state in all django Server objects (consider concurrency)
* add an auth script for UDP that checks against a dango user

## Policy

* implement

## Cloud

* actuate Route53 changes on Server.save() for connect=True/False

## Miscelaneous

* setup support@evon.link email and add to cli and web admin
* setup webpage
* publush on AWSMP, indicate that inbound tcp/443, tcp/80, udp/1194 are required
* address TODO, FIXME, XXX comments
* in django admin, show related properties of user models, ie. show tokens in the auth.Users app
* default admin password is ec2 id. Force change first login.
* during hub deploy, wtf is this: Extracting...cpio: ././@LongLink not created: newer or same age version exists 
* ✅ rename systemd service to evonhub
* in bootstrap, send enc payload to hub for decrypt, with optional local decrypt (use same EVON_DEPLOY_KEY for both, try local decrypt, then remote).
* ✅ add max server count check to auth.py
* implement last_seen on server objects
* consider redirecting all hub urls to django app in nginx. SSL certs and ALLOWED_HOSTS needs to be managed accordingly. Alternate/simpler: allow clients to choose their own domain prefix rather than the 5 character auto-generated one.
