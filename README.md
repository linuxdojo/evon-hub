![EVON Logo](assets/evon_logo.png)
# Evon Hub

Evon Hub is the core component of the Evon system, acting as the central network hub for connected servers, users and policy. It provides a web application and an API along with OpenVPN services for overlay network connectivity.

Evin Hub must be deployed on an AWS EC2 instance running Amazon Linux 2.

## Deployment

To deploy, run command:
```
make <EC2_FQDN> ENV=<ENV> DOMAIN_PREFIX=<PREFIX> SUBNET_KEY=<SK> deploy

```
Where:
* `<ENV>` is one of `dev`, `staging`, `prod`
* `<EC2_FQDN>` is the FQDN of the target EC2 instance to which you have SSH access to the `ec2-user` using public key authentication.
* `<PREFIX>` is the first label of the new Hub FQDN, which will become `<PREFIX>.env.evon.link` (where env is one of 'dev', 'staging', or empty for prod). The Web UI and API can be reached via HTTPS to the Hub FQDN.
* `<SK>` is the subnet key, it must be between 64 and 127 inclusive. The overlay subnet for the deployed Hub becomes `100.<SUBNET_KEY>.224.0/19`

Example:
```
make EC2_HOST=ec2-13-236-148-138.ap-southeast-2.compute.amazonaws.com ENV=dev DOMAIN_PREFIX=o82ml SUBNET_KEY=111 deploy
```
Durations:
* A fresh deploy takes approximately 12 mins on a newly provisioned t2.micro instance.
* A re-deploy takes approximately 2 mins on the same system.

## Usage

Once deployed, the Hub WebUI can be reached at `https://<PREFIX>.env.evon.link`. Default credentials are:
|   |   |
|---|---|
|__Username__| admin |
|__Password__| `<EC2 Instance ID of Hub>` |
