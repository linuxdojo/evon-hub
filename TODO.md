# API

* fix errors and warnings re Hello and Server endpoints on runserver start -> read api docs

# Logging

* ensure all django events are logged

# CLI

* add change-deploy-api-key feature to evon cli

# Users

* make superuser and apiuser (deployer?) immutable

# Bootstrap

* update docker bootstrap to support latest hub api setup

# OpenVPN

* create auth-user-pass-verify script for `evon-hub/templates/openvpn/server/server_tcp.conf`
 * create user-selectable UUID as a bootstrap option so that not too many ip addresses are consumed in vpn subnet for Alpine users (they are ephemeral). Consider how to use the password field properly in item 7 above.
 * check for duplicate (currently connected) uuid and reject if so
 * consider discovery|operational modes via custom login scripts for server acquisition vs. changeless op mode

# General

* setup support@evon.link email and add to cli and web admin
* setup webpage

# Hub Installer

* at the start of the evon-hub installer shell script, check if inbound tcp/443, tcp/80, udp/1194 are open before continuing
* address TODO's in installer, around s3 publishing and upgrading process

# Mapper

* implement

# Policy

* implement
