# MVP Release

## AWSMP

* implement s3 package publishing and upgrading process. Wait until we understand how AWS MP SaaS works first.
* publish on AWSMP
* if update available, add warning notification on superuser login.
* update "make package" target to pre-install rpms and pyenv and pip packages
* if you have profanity in domain_prefix, you just get this failure in evon-deploy. fix it:
```
### Obtaining and persisting account info...
2022-10-25 13:50:33,281 - INFO: cli.main[209]: Evon client v1.0.194 starting - 3.10.5 (main, Oct 25 2022, 13:44:43) [GCC 7.3.1 20180712 (Red Hat 7.3.1-15)]
2022-10-25 13:50:33,291 - INFO: cli.main[229]: registering account...
2022-10-25 13:50:35,195 - ERROR: evon_api.do_request[63]: POST request failed: '400 Client Error: Bad Request for url: https://api.dev.evon.link/zone/register'
...
```
* installer bombs with:
```
MySQLdb.ProgrammingError: (1146, "Table 'evon.auth_permission' doesn't exist")
...
```

# Future Release

* create a new persisted secret key in settings.py when deploying, see https://saasitive.com/tutorial/generate-django-secret-key/
* tidy up syslog to log all app related logs to the existing single evon log single file in /var/log/evon/ and consider adding get_syslog_logs api endpoint
* consider a "refresh" button on list views in admin
* Fix warnings when clients connect::
``````
WARNING: 'link-mtu' is used inconsistently, local='link-mtu 1544', remote='link-mtu 1543'
WARNING: 'comp-lzo' is present in local config but missing in remote config, local='comp-lzo'
``````
on the client end:
```
Oct 19 10:02:58 umbriel nm-openvpn[1150313]: WARNING: 'link-mtu' is used inconsistently, local='link-mtu 1541', remote='link-mtu 1557'
Oct 19 10:02:58 umbriel nm-openvpn[1150313]: WARNING: 'keysize' is used inconsistently, local='keysize 128', remote='keysize 256'
```
* pages for 500, 404 and 404 (when deleting admin/deployer users from signals)
* replace evon cli and its sudo wrappers in /usr/local/bin with eapi manage commands
* add tooltips top Admin group objects to show members at a glance
* rename policy.servergroups to policy.target_server_groups and policy.servers to policy.target_servers
* add a connected bool field to UserProfile and show in admin User list
* documentation (readthedocs/sphinx style)
* consider redirecting all hub urls to django app in nginx. SSL certs and ALLOWED_HOSTS needs to be managed accordingly. Alternate/simpler: allow clients to choose their own domain prefix rather than the 5 character auto-generated one.
* default admin password is ec2 id. Force change first login.
* add mfa (consider django-mfa2 or django-mfa3)
* we're filtering permissions in the permission API list view and in the admin site for User and Group auth classes, but not enforcing exclusive use of this filtered list in the save() (at least for the API). Consdiering only Superusers can change perms and if they bugger around with saving unlisted permission id's, it's their prob. We'll enforce this later.
