![EVON Logo](assets/evon_logo.png)
# WARNING: This is an old document that needs rework
# evon.link - Elastic Virtual Overlay Network

1. [Description](#description)
    * [Services](#services)
    * [VPN Network Range](#vpn-network-range)
2. [Deployment Mapper](#deployment-mapper)
    * [Logging](#logging)
3. [Linking an existing server to EVON](#linking-an-existing-server-to-evon)
    * [Troubleshooting](#troubleshooting)
        - [bootstrap.sh issues](#bootstrapsh-issues)
        - [Deploying OpenVPN on CentOS6](#deploying-openvpn-on-centos6)
        - [Alternate .com FQDN](#alternate-com-fqdn)
4. [Listing Deployments](#listing-deployments)
5. [Connecting to Deployments](#connecting-to-deployments)
    * [1. SSH Access](#1-ssh-access)
    * [2. VPN Admin Access](#2-vpn-admin-access)
6. [Security](#security)
    * [Known Security Risks](#known-security-risks)
        - [Client to Client Communications](#client-to-client-communications)
        - [OpenVPN duplicate-cn Enabled](#openvpn-duplicate-cn-enabled)
    * [Controlling Squid Access](#controlling-squid-access)
    * [Secrets Storage Location](#secrets-storage-location)
    * [Managing OpenVPN Certificates and Keys](#managing-openvpn-certificates-and-keys)
7. [Development](#development)
    * [Deploying New Changes](#deploying-new-changes)
    * [Makefile targets](#makefile-targets)
    * [The evon.link Server](#the-evonlink-server)

## Description

The evon.link is a hub-spoke topology based connectivity system for Linux servers. The EVON server resides at fqdn `evon.link` and hosts SSH and OpenVPN (publically), and Squid (privately). Connected servers are fully reachable through IPv4 routing by authorised admins, and can use the Squid service on `evon.link` to reach the Internet.

The software component in this directory creates an installable artefact named `bootstrap.sh` and publishes it to `https://<username>:<password>@evon.link/bootstrap` for download via wget or curl on any new or existing server. CentOS 6 and 8 are supported.

Running `bootstrap.sh` on a server and providing it with a valid decryption password will make the following changes to the system:

- OpenVPN is installed, configured, persisted and connected to the EVON server at `evon.link`. The deployment will be online and available for centralised management. VPN connections are resilient and infinitely retry reconnection in the case of outages of any sort.
- A new interface will have been created on the server named `tun0` and assigned a dynamic address in the `10.111.0.0/16` subnet.
- Two new minimum-scoped /32 routes are added for connectivity to the VPN server only, thus not disrupting any existing routing or network configuration (see example below).These two added routes are auto-removed when the VPN is disconnected for any reason.
- Configuration enabling the endpoint server to use the Squid proxy service on evon.link for outbound Internet access (10.111.0.1 on TCP/3128) via the VPN tunnel by setting `http_proxy` and `https_proxy` env vars in `/etc/profile.d/evon_proxy.sh`.

This component also deploys a Deployment Mapper service on the EVON server which auto-creates new public FQDN records named `<hostname>.evon.link` (see below under Deployment Mapper for further info).

### Services

`evon.link` exposes the following network services:

| Service | Protocol/Port               | Exposure                               | Authentication   |
|---------|-----------------------------|----------------------------------------|------------------|
| OpenVPN | TCP/443, TCP/1194, UDP/1194 | Public                                 | TLS Key/Cert     |
| OpenSSH | TCP/443, TCP/22             | Public, Whitelist Controlled           | PKA Only         |
| HTTP(s) | TCP/443, TCP/80             | Public                                 | HTTP Basic Auth  |
| Squid   | TCP/3128                    | VPN Clients Only, Blacklist Controlled | None             |

### VPN Network Range

The 10.111.0.0/16 VPN network must not conflict with any existing subnets on server networks. If there is a conflict, the VPN network can be changed.

## Deployment Mapper

Deployment Mapper is a cron-triggered, short lived service that maps the IPv4 VPN addresses of clients (only) to a publically resolvable FQDN at `<hostname>.evon.link`. While these FQDN's are publically resolvable, they only resolve to private 10.111.0.0/16 addresses that are not reachable unless SSH'd into `evon.link` server or via an Admin connection to the EVON VPN service. For security, the `*.evon.link` records are not publically enumerable. See below under "Connecting to Deployments as an Admin user".

The `<hostname>` component of the FQDN will be the Linux hostname of the server itself (returned by the `hostname` command on the deployment), thus hostnames must be globally unique. However, should multiple servers have the same hostname (or when the hostname is not able to be identified by Deployment Mapper due to connectivity issues), the duplicates' fqdn's will become `<dashed-ipaddress>.evon.link`, where `<dashed-ipaddress>` is the VPN-assigned IPv4 address with the periods swapped for dashes, eg: `10-111-0-6.evon.link`. Simply updating the hostname of a connected server to a unique name at any time will cause the FQDN to automatically change to reflect the new hostname within 5 minutes.

As the EVON VPN assigned IP addresses are dynamically assigned, a deployment's VPN IP addresses may change at any time, eg. when a temporary connection outage occurs and recovers. DNS is automatically updated every 5 minutes to reflect such changes, abd all `*.evon.link` records are given a TTL value of 60 seconds so that DNS resolution is accurate within a reasonably small amount of time.

DNS records are automatically removed when systems are disconnected from the VPN, and re-created when they re-join.

The Deployment Mapper cron trigger config is at location `/etc/cron.d/deployment_mapper`. It can be manually run by SSH'ing to `admin@evon.link` and running the command:
```
/opt/deployment_mapper/deployment_mapper.py
```

### Logging

Deployment Mapper logs all activity including DNS record update events to syslog on the evon.link server at `/var/log/messages`. To filter, grep for the string `deployment_mapper`.

## Linking an existing server to EVON

The bootstrap script is obtainable on any server (CentOS6 or CentOS8 based) via command:
```
curl https://<username>:<password>@evon.link/bootstrap > bootstrap.sh; chmod +x bootstrap.sh
```
Refer to the Security section below to obtain username and password values for this URL.

If the environment in which the server is deployed requires a proxy server for Internet access, you may specify the proxy settings in the curl command, eg:
```
curl --proxy "http://<proxy_username>:<proxy_password>@<proxy_host>:<proxy_port>"  https://<username>:<password>@evon.link/bootstrap > bootstrap.sh; chmod +x bootstrap.sh
```
NOTE: If you are on a network whose proxy server uses NTLM authentication, you can use the switch `--proxy-ntlm` in the curl arguments. Similarly, `--proxy-digest` can be used for digest authentication.

Once downloaded, run the bootstrapper script to install OpenVPN and connect the deployment to EVON. Type:
```
./bootstrap.sh
```
An AES-256 decryption passphrase will be requested by the bootstrap script to decrypt the OpenVPN client configuration. See the Security section below for info about obtaining this passphrase.

For info about uninstallation of OpenVPN on the deployment, or how to perform a non-interactive installation of the bootstrap script, type
```
./bootstrap.sh --help
```
### Troubleshooting

#### bootstrap.sh issues

The `bootstrap.sh` script is idempotent and can be run at any time to resume a failed installation. It will not perform any changes if it detects an existing healthy connection to the EVON service.

#### Deploying OpenVPN on CentOS6

The `bootstrap.sh` script installs OpenVPN via `yum`. If it fails, you can install it manually. Download the following packages to the deployment:

- <https://archives.fedoraproject.org/pub/archive/epel/6/x86_64/Packages/o/openvpn-2.4.9-1.el6.x86_64.rpm>
- <https://archives.fedoraproject.org/pub/archive/epel/6/x86_64/Packages/l/lz4-r131-1.el6.x86_64.rpm>
- <https://archives.fedoraproject.org/pub/archive/epel/6/x86_64/Packages/p/pkcs11-helper-1.11-3.el6.x86_64.rpm>

Alternatively, get the packages directly from the EVON server itself:

```
curl 'https://<username>:<password>@evon.link/support/el6/lz4-r131-1.el6.x86_64.rpm' > lz4-r131-1.el6.x86_64.rpm
curl 'https://<username>:<password>@evon.link/support/el6/openvpn-2.4.9-1.el6.x86_64.rpm' > openvpn-2.4.9-1.el6.x86_64.rpm
curl 'https://<username>:<password>@evon.link/support/el6/pkcs11-helper-1.11-3.el6.x86_64.rpm' > pkcs11-helper-1.11-3.el6.x86_64.rpm
```
Then, install them with command:
```
rpm -ivh *.rpm
```
Then, re-run `bootstrap.sh`

## Listing Deployments

An inventory list of all deployments showing their `<hostname>.evon.link` FQDN and associated VPN IP address can be obtained anywhere on the Internet by running (or browsing to):
```
curl https://<username>:<password>@evon.link/inventory
```
Refer to the Security section below to obtain username and password values for this URL.

When SSH'd into the evon.link server, the inventory list can be obtained by typing:
```
list_inventory
```
SSH'ing to `evon.link` is whilelist controlled. Use the username `admin` in your SSH client. SSH public key auth only is available.

## Connecting to Deployments

There are two methods of connecting to servers for Admin users:

### 1. SSH Access

All EVON-connected deployments are reachable by first SSH'ing to `admin@evon.link`, then connecting to the hostname of the desired server, eg:
```
# listing deployments:

$ list_inventory
{"ldlab-centos6-server1.evon.link": "10.111.0.14"
,"ldlab-centos8-server1.evon.link": "10.111.0.6"}
$ 


# ping example:

$ ping ldlab-centos8-server1
PING ldlab-centos8-server1.evon.link (10.111.0.6) 56(84) bytes of data.
64 bytes from ip-10-111-0-6.ap-southeast-2.compute.internal (10.111.0.6): icmp_seq=1 ttl=64 time=9.62 ms
64 bytes from ip-10-111-0-6.ap-southeast-2.compute.internal (10.111.0.6): icmp_seq=2 ttl=64 time=11.5 ms
64 bytes from ip-10-111-0-6.ap-southeast-2.compute.internal (10.111.0.6): icmp_seq=3 ttl=64 time=11.2 ms
^C
--- ldlab-centos8-server1.evon.link ping statistics ---
3 packets transmitted, 3 received, 0% packet loss, time 5ms
rtt min/avg/max/mdev = 9.617/10.745/11.464/0.807 ms
$ 


# connecting to a deployment with SSH:

$ ssh root@ldlab-centos6-server1
Last login: Sat Mar 27 22:08:34 2021 from 10.111.0.1
(http://www.unifiedrecording.com)
[root@ldlab-centos6-server1 ~]# 

```
Note that:
- Only the short name is required, the `.evon.link` domain suffix is optional as it is auto-added by the resolver configured in `/etc/resolv.con` on the EVON server.
- No password is required to SSH to any deployment because the `admin` user's SSH public key is auto-synched to the server's root user by the bootstrap script

### 2. VPN Admin Access

Admin users are able to connect to the evon.link VPN and access any service on any VPN-connected server via their `*.evon.link` FQDN directly from their workstations. The OpenVPN Admin client configuration file is available by request to authorised administrators only.

To enable use of short names (omitting the `.evon.link` domain suffix) when connecting to endpoints, add `evon.link` as a search suffix on your development workstation.

## Security

There are multiple layers of security for the EVON system.

1. The `evon.link` domain is in no way linked to any other customer-owned domain.
2. The `*.evon.link` DNS records are not publically enumerable, and resolve to unreachable RFC 1918 addresses unless securely SSH'd or VPN'd to the evon.link server.
3. SSH access to evon.link is controlled via a whitelist using an AWS EC2 Security Group.
4. VPN access to evon.link is controlled via SSL keys and certificates, and TLS auth is enabled to mitigate DoS attacks and attacks on the TLS stack
5. OpenVPN processes drop priveleges to nobody:nobody after starting on evon.link server
6. OpenVPN client-to-client communications is disabled for VPN clients (see below in Risks). Two new minimum-scoped /32 routes are inserted to VPN clients for connectivity to the VPN server only, allowing access to Squid.
7. SELinux is enabled and tuned to disallow access to unneeded resources by OpenVPN, NginX and all other running services and daemons on the evon.link server.
8. All HTTP (eg. curl) requests to EVON require a username and password (basic auth over HTTPS)
9. The bootstrap.sh installer itself needs a secret key to decrypt the AES-256 protected OpenVPN configuration when run.
10. The Deployment Mapper component requires revocable AWS API keys that are limited in ability to only update Route53 for maintaining the `<hostname>.evon.link` DNS records.
11. No sensitive information or secrets are stored in unencrypted clear text within Git.
12. Squid access is controllable for each connected server (see below under "Controlling Squid Access")
13. Only SSH public key auth is available on the EVON server.
14. fail2ban is enabled blocking brute force attacks on the SSH service
15. Security patches are automatically downloaded and installed daily on the evon.link server. The following services are auto-restarted if a securty update is applied: sshd, openvpn, nginx

### Known Security Risks

#### Client to Client Communications
While client-to-client communications is blocked within the OpenVPN stack (item 6 above), the evon.link server has ipv4 routing enabled in the kernel to allow Admin VPN users to connect to any deployment. When an Admin connects to the VPN, the following route is automatically pushed to them:
```
10.111.0.0/16 via 10.111.x.x dev tun0  # x.x is the dynamic vpn peer ip address assigned to the Admin VPN client
```
This route is **not** pushed to server endpoints, only to admin workstations. It is possible however for this route to be manually added by a root user to a VPN-connected server, which would allow it to reach other deployments connected to the VPN network. If root access is controlled on servers, and information about the VPN subnet is kept private, risk exposure will remain minimal. 

#### OpenVPN duplicate-cn Enabled

For convenience and automation the `duplicate-cn` option in the OpenVPN server config is enabled, meaning all servers use a common SSL key to connect. Whilst the OpenVPN client SSL key is strongly protected by both HTTP/s and Basic Auth for retrieval, and by AES-256 for subsequent decryption, there is still a small possibility that the key may leak due to administrative mismanagement. Should this occur, a new SSL key pair can be generated on the OpenVPN Easy-RSA3 CA and distributed to all servers via uninstalling and reinstalling a newly built `bootstrap.sh` script. See below for info about Revoking, Rotating or Renewing OpenVPN Certificates and Keys.

### Controlling Squid Access

A server-side Squid blacklist can be edited to block Internet access to any server based on its fqdn or hostname. To do so, edit the following file on the `evon.link` server:
```
/etc/squid/blacklist.conf
```
Instructions for maintaining the blacklilst reside at the top of this file.

### Secrets Storage Location

All secrets/credentials/passwords/API keys are stored within PCI-compliant secure storage and are available via the EVON AWS account within Secrets Manager [here](https://ap-southeast-2.console.aws.amazon.com/secretsmanager/home?region=ap-southeast-2#!/secret?name=bootstrapper) (AWS auth required for access).

### Managing OpenVPN Certificates and Keys

Should the need arise to rotate, revoke or renew OpenVPN's server or client keys and certificates, see:

https://linuxdojo.atlassian.net/wiki/spaces/CLIEN/pages/33521665/EVON+OpenVPN+CA+Config

## Development

### Deploying New Changes

If changes are made to any file within this directory, they will need to be deployed to evon.link server.

In order to deploy changes, you will need your SSH public key added to the `admin` user on the evon.link server.

To deploy changes, run the command:
```
make deploy
```

### Makefile targets

The Makefile in this directory supports functions including updating the encryption key password for the OpenVPN secrets config file, building the bootstrap.sh script and deploying it and the deployment mapper script to the evon.link server.

For a list of targets and descriptions, run:
```
make
```

### The evon.link Server

Manual configuration has been applied to the AWS EC2 instance hosting the evon.link server including iptables, sslh, Squid, NginX, Certbot, Openvpn, SELinux, fail2ban, etc. The underlying fully-configured EBS storage device on the EC2 instance has been backed up via snapshot in the AWS EC2 management console.

