![EVON Logo](assets/evon_logo.png)
# Evon Hub

Evon Hub is the core component of the Evon system, acting as the central network hub for connected servers, users and policy. It provides a web application and an API along with OpenVPN services for overlay network connectivity.

Evin Hub must be deployed on an AWS EC2 instance running Amazon Linux 2.

## Deployment

### Publishing only

To copy the Evon Hub installer script to a remote EC2 instance run the below command. Once published, the script must subsequently be run on the Hub via SSH.
```
make ENV=<ENV> EC2_HOST=<EC2_FQDN> publish
```

### Publishing and deploying

To copy and also run the Evon Hub installer script on a remote EC2 instance in one command, run:
```
make ENV=<ENV> EC2_HOST=<EC2_FQDN> RUN_INSTALLER=<true|false> DOMAIN_PREFIX=<PREFIX> SUBNET_KEY=<SK> deploy
```

### Arguments

* `<ENV>` is one of `dev`, `staging` or `prod`
* `<EC2_FQDN>` is the FQDN of the target EC2 instance to which you have SSH access to the `ec2-user` using public key authentication.
* `<PREFIX>` is the first label of the new Hub FQDN, which will become `<PREFIX>.env.evon.link` (where env is one of 'dev', 'staging', or empty for prod). The Web UI and API can be reached via HTTPS to the Hub FQDN.
* `<SK>` is the subnet key. It must be between 64 and 127 inclusive. The overlay subnet for the deployed Hub becomes `100.<SUBNET_KEY>.224.0/19`

### Example

Example publish and deploy:
```
make ENV=dev EC2_HOST=ec2-13-236-148-138.ap-southeast-2.compute.amazonaws.com RUN_INSTALLER=true DOMAIN_PREFIX=mycompany SUBNET_KEY=111 deploy
```

Deployment durations:
* A publish and deploy on a fresh t2.micro EC2 instance takes approximately 12 mins.
* Subsequent publish and deploy operations take approximately 2 mins on the same system.

## Usage

Once published and deployed, the Hub WebUI can be reached at `https://<PREFIX>.<env>.evon.link` (`<env>` is ommited if `prod`).

Default Web UI login credentials are:
|   |   |
|---|---|
|__Username__| admin |
|__Password__| `<EC2 Instance ID of Hub>` |
