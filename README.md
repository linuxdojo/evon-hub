![EVON Logo](assets/evon_logo.png)
# Evon Hub

## Deployment

To deploy, run command:
```
make <EC2_FQDN> ENV=<ENV> deploy
```
Where:
* `<ENV>` is one of `dev`, `stag`, `prod`
* `<EC2_FQDN>` is the FQDN of the target EC2 instance to which you have SSH access to the `ec2-user` using public key authentication.

Example:
```
make EC2_HOST=ec2-13-239-63-235.ap-southeast-2.compute.amazonaws.com ENV=dev deploy
```
A fresh deploy takes approximately 10 mins on a newly provisioned t2.micro instance.
A re-deploy takes approximately 2 mins on the same system.
