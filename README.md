![EVON Logo](assets/evon_logo_e.png)

# Evon Hub

[Evon Hub](https://evonhub.com) is an overlay network application, similar to Tailscale but built using OpenVPN. It uses a hub-spoke topology, with the software in this repository acting as the hub. It includes a web interface and API, and allows any device running OpenVPN to connect as a server or as a client. Servers and clients obtain static IPv4 addresses on the overlay network on the 100.x.y.x (CGNAT) address space, and can obtain unique public domain names. The hub allows rules and policies to be created that govern which servers and services can be reached by users and other servers on the overlay network. The transport used is SSL over TCP/443, allowing systems to access the hub via commonly open channels, including via web proxy servers.

## Installation

There are 3 modes of installation:

1. Opensource community version (fully functional, no limitations), see "Quick Start" below
1. Hosted SaaS, via [https://evonhub.com](https://evonhub.com)
1. Hosted SaaS, via [AWS Marketplace](https://aws.amazon.com/marketplace/pp/prodview-xgpcsmkmv3sny)

## Quick Start

* Clone this repository
* Create and activate a Python 3.10.5 virtual environment
* Run the following command to build the installer package:
```
make package-oss
```
This will create a file named `evon-hub-standalone_<version>.sh`
* Create a fresh Rocky/AlmaLinux 9 VPS instance with a public IPv4 address, and assign a domain name to it, eg "hub.example.com"
* Ensure the following protocols/ports are allowed inbound:
  * tcp/22 (for your remote shell/management only, using a high port and/or source IP address filtering is recommended)
  * tcp/80
  * tcp/443
  * udp/1194
* Copy the installer file to the VPS and run it with command (substituting your domain name)
```
sudo bash evon-hub-standalone_<version>.sh --domain-name hub.example.com
```
The installation will take several minutes, with instructions printed at the end for accessing your hub.

### Optional: Setup Automatic DNS entries for connected servers

Each connected system (servers, devices, etc) obtains a static IPv4 address on the 100.x.y.z network subnet.

Connected servers can also obtain unique DNS names in the format `<hostname>.hub.example.com` using the domain name in the above example. This feature is automatically setup on hosted SaaS deployments, and can be setup in the opensource community version by editing the file `/opt/evon_standalone_hook` and adding code to update your own DNS zone for your chosen domain.

## Local Development

Local development assumes you are running a recent Linux distribution if you wish to run the EvonHub app locally on your development machine.

* Create and activate a virtualenv using Python 3.10.5
* run `make setup-local`
* start the development webserver by running `make runserver`. The web UI can then be reached by browsing to [http://localhost:8001](http://localhost:8001). The default login credentials for the development server are `admin/admin`.

## Documentation

Documentation can be found at [https://docs.evonhub.com](https://docs.evonhub.com)

## License

The software in this repository is released under the GNU GPLv3.

See file `LICENSE.txt`  for details.
