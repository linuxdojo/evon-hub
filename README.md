![EVON Logo](assets/evon_logo_e.png)

# Evon Hub

[Evon Hub](https://evonhub.com) is an overlay network application, built upon OpenVPN. It allows you to join servers and devices together over the internet, bringing them right next to each other, and to you and your users as if they were on a simple LAN, despite their physical location. 

Evon Hub uses a hub-spoke topology, provides a web interface and API, and allows any device running OpenVPN to connect. Connected systems obtain static IPv4 addresses on the overlay network on the 100.x.y.x (CGNAT) address space, and can obtain unique public domain names. The hub allows rules and policies to be created that govern which servers and services can be reached by users and other servers on the overlay network. The transport used is SSL/TLS over TCP/443, allowing systems to connect to the hub via commonly open channels, including via web proxy servers.

There are 2 modes of installation:

1. Open Source Community Version (fully functional, no limitations)
1. Hosted SaaS (commercial with support), via [https://evonhub.com](https://evonhub.com) or via [AWS Marketplace](https://aws.amazon.com/marketplace/pp/prodview-xgpcsmkmv3sny)

## Installation

* Obtain the lastest release installer file from [Releases](https://github.com/linuxdojo/evon-hub/releases).
* Create a fresh Rocky/AlmaLinux 9 VPS instance with a public IPv4 address, and assign a domain name to it, eg "hub.example.com"
* Ensure the following protocols/ports are allowed inbound:
  * tcp/22 (for your remote shell/management only, using a high port and/or source IP address filtering is recommended)
  * tcp/80
  * tcp/443
  * udp/1194
* Copy the installer file to the VPS and run it with the below command, substituting your own domain name in place of `hub.example.com`, see [Automatic DNS](#automatic-dns) below for detail about DNS setup.
```
sudo bash evon-hub-standalone_<version>.sh --domain-name hub.example.com
```

The installation will take several minutes, with instructions printed at the end of the install log for how to access your hub.

### Automatic DNS

Connected servers can obtain unique DNS names in the format `<hostname>.<domain-name>`, eg `myserver.hub.example.com`. This feature is automatically provided on hosted SaaS deployments only, but can be setup in the open source community version by editing the file `/opt/evon_standalone_hook`. This file is provided as a BASH script, but may be written in any language. It is setup to work with AWS Route53 hosted domains, however you can modify it to update any DNS service that supports programatic record updates. Instructions and implementation details are provided as comments at the top of the file.

## Updating your Hub

Updates to SaaS installations are automatic. To update the Open Source Community Version, simply download the [latest release](https://github.com/linuxdojo/evon-hub/releases) and re-run it on your Hub in the same way as described in the [Installation](#installation) section above.

# Development

Local development assumes you are running a recent Linux distribution if you wish to run the EvonHub app locally on your development machine.

* Clone this repository on your development workstation.
* Create and activate a virtualenv using Python 3.10.5
> [!NOTE]
> You may need a tool like pyenv to first install Python 3.10.5, but, if you're cloning the code on your target EvonHub server rather than on your development workstation, make sure that pyenv installs Python 3.10.5 in, for example, `/opt/pyenv` rather than default location of `~/.pyenv`, else the low priveleged user that runs the evonhub service can't reach into the user's home to access Python. Then create your virtualenv in `./.env` in the cloned Evonhub repo, and activate it before continuing.
* run `make setup-local`
* start the development webserver by running `make runserver`. The web UI can then be reached by browsing to [http://localhost:8001](http://localhost:8001). The default login credentials for the development server are `admin/admin`.

## Building your own installer file

You can build your own installer file, similar to what is provided in [Github latest releases](https://github.com/linuxdojo/evon-hub/releases). To do so, run the following command:
```
make package-oss
```
This will create an installer file named `evon-hub-standalone_<version>.sh`.

# Documentation

Documentation can be found at [https://docs.evonhub.com](https://docs.evonhub.com)

# License

The software in this repository is released under the GNU GPLv3.

See file `LICENSE.txt`  for details.
