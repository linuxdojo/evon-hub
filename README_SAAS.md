## SaaS Deployment Information

SaaS deployment requires API keys private to evonhub.com. For the full featured, unrestricted opensource community version, please refer to the README.md file in this directory.

### Arguments Reference

The below invocations make reference to these arguments:

* `<ENV>` is one of `dev`, `staging` or `prod`
* `<TARGET_FQDN>` is the FQDN of the target instance to which you have SSH access to the `ec2-user` or a user with full sudo access using public key authentication.
* `<PREFIX>` is the first label of the new Hub FQDN, which will become `<PREFIX>.<ENV>.evon.link`. `<ENV>` is omitted for prod.
* `<SK>` is the subnet key. It must be between 64 and 127 inclusive. The overlay subnet for the deployed Hub becomes `100.<SUBNET_KEY>.224.0/19`

### Publishing installer only

To copy the Evon Hub installer script to a remote instance, run the below command. Resultant package will be at path `~/bin/evon-deploy` which is assumed to be in the target user's `$PATH`. Once published, the script must subsequently be run on the Hub via SSH.
```
make HOSTED_MODE=awsmp ENV=<ENV> TARGET_HOST=<TARGET_FQDN> publish
```

### Publishing an updated version of Evon Hub for customers

Deployments are able to udpate/autoupdate themselves. To publish an update, run
```
make HOSTED_MODE=awsmp ENV=<env> publish-update
```
This will put the package in S3, ready to be picked up by deployments during next auto/manual update run.


### Building an EC2 instance ready for converting to an AMI or other image

| :memo: If not selfhosted, the target EC2 must be freshly installed in the `us-east-1` region |
|----------------------------------------------------------------------------------------------|

```
make HOSTED_MODE=awsmp ENV=<ENV> TARGET_HOST=<TARGET_FQDN> deploy-base
```
Once done, if not selfhosted, manually export the EC2's EBS device as an AMI. For the related procedure, refer to [EVON AWS Marketplace Integration docs](https://linuxdojo.atlassian.net/wiki/spaces/EVON/pages/138379265/AWS+Marketplace+Integration)

### Deploy to Staging Environment for AWS Marketplace deployments

* subscribe and deploy Evon Hub from AWS Marketplace
* use `make HOSTED_MODE=awsmp ENV=staging TARGET_HOST=<TARGET_FQDN> publish` to upload latest deploy script
* ssh to the EC2 isntance and run `evon-deploy` as the ec2-user

### Deploying to a test EC2 instance (any region)

For development purposes, to copy and also run the Evon Hub installer script on a remote EC2 instance in one command, run:
```
make ENV=<ENV> HOSTED_MODE=awsmp TARGET_HOST=<TARGET_FQDN> DOMAIN_PREFIX=<PREFIX> SUBNET_KEY=<SK> deploy-test
```

### Selfhosted Deploy

Selfhosted mode supports creating an Evon Hub instance on a non-EC2 host that is not coupled to AWS Marketplace. It must be running EL8, EL9 or a clone (eg Rocky 8 or 9). Add `HOSTED_MODE=selfhosted` to your env when running `make` to activate selfhosted mode. Omitting this env var will assume the target is an EC2 host, intended for deployment via AWS Marketplace subscription.

### Quick Deploy

This is a convenience target for developers to quickly sync local project elements to remote dev instance. It requires that root ssh with pub key auth has been setup.

### Example

Example publish and deploy:
```
make ENV=dev HOSTED_MODE=awsmp TARGET_HOST=ec2-13-236-148-138.ap-southeast-2.compute.amazonaws.com RUN_INSTALLER=true DOMAIN_PREFIX=mycompany SUBNET_KEY=111 deploy-test
```

Deployment durations:
* A publish and deploy on a fresh t2.micro EC2 instance takes approximately 12 mins.
* Subsequent publish and deploy operations take approximately 2 mins on the same system.

## Usage

Once published and deployed, the Hub WebUI can be reached at `https://<PREFIX>.<env>.evon.link` (`<env>` is ommited if `prod`).

Default Web UI login credentials are:
| | |
|--------|----------------------------|
|Username| admin                      |
|Password| `<Instance ID of Hub>`     |
