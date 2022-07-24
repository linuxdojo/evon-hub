.SILENT:

help: # Show this help
	@echo Make targets:
	@egrep -h ":\s+# " $(MAKEFILE_LIST) | \
	  sed -e 's/# //; s/^/    /' | \
	  column -s: -t

.PHONY: all bootstrap

bootstrap: # Append OpenVPN config payload (with encrypted secrets) to bootstrap_template.sh and write to bootstrap.sh
	echo "Building bootstrap..."
	[ -e openvpn_secrets.conf.aes ] || make encrypt
	cp bootstrap_template.sh bootstrap.sh
	tar -c openvpn_client.conf openvpn_proxy.conf openvpn_secrets.conf.aes | gzip | base64 >> bootstrap.sh
	chmod +x bootstrap.sh
	echo "Done."

deploy: # Build and deploy latest bootstrap.sh and deployment_mapper to {{ account_name }}.evon.link
	# build and deploy bootstrap
	make bootstrap
	echo "Deploying bootstrap..."
	scp bootstrap.sh ec2-user@{{ account_name }}.evon.link:/tmp
	ssh ec2-user@{{ account_name }}.evon.link " \
		sudo mv -f /tmp/bootstrap.sh /var/www/html/; \
		sudo rm -f /var/www/html/bootstrap; \
		sudo ln -s /var/www/html/bootstrap.sh /var/www/html/bootstrap; \
		"
	# deploy deployment mapper and cron trigger
	rm -f /tmp/deployment_mapper.tgz >/dev/null 2>&1 || :
	cd deployment_mapper && tar -zcvf /tmp/deployment_mapper.tgz .env deployment_mapper.py requirements.txt deployment_mapper.cron && cd ..
	scp /tmp/deployment_mapper.tgz ec2-user@{{ account_name }}.evon.link:/tmp
	rm -f /tmp/deployment_mapper.tgz
	ssh ec2-user@{{ account_name }}.evon.link " \
		sudo mkdir -p /opt/deployment_mapper; \
		sudo mv /tmp/deployment_mapper.tgz /opt/deployment_mapper; \
		cd /opt/deployment_mapper; \
		sudo tar xf deployment_mapper.tgz; \
		sudo chmod +x deployment_mapper.py; \
		sudo rm -f deployment_mapper.tgz; \
		sudo pip3 install -r requirements.txt; \
		sudo cp /opt/deployment_mapper/deployment_mapper.cron /etc/cron.d/deploymentmapper; \
		sudo chown root:root /etc/cron.d/deploymentmapper; \
		"
	# done
	echo "Done: "
	echo "  - new bootstrap is now available at https://<username>:<password>@{{ account_name }}.evon.link/bootstrap"

encrypt: # Encrypt openvpn_secrets.conf and output as openvpn_secrets.conf.aes
	echo "  WARNING: ***************************************************************************"
	echo "    Please ensure you use a strong password to encrypt the OpenVPN secrets.           "
	echo "    This password will be requested by bootstrap.sh when it is run on endpoint servers."
	echo "  ************************************************************************************"
	openssl enc -aes-256-cbc -in openvpn_secrets.conf -out openvpn_secrets.conf.aes 2>/dev/null
	echo Done.

decrypt: # Decrypt openvpn_secrets.conf.aes as openvpn_secrets.conf (openvpn_secrets.conf is gitignored)
	[ -e openvpn_secrets.conf ] \
		&& echo "Please delete or move openvpn_secrets.conf first (refusing to overwrite)." \
		|| openssl enc -d -aes-256-cbc -in openvpn_secrets.conf.aes -out openvpn_secrets.conf 2>/dev/null
	echo "  WARNING: ***********************************************************************"
	echo "    Never commit the decrypted secrets to Git!                                    "
	echo "    Note that openvpn_secrets.conf (the cleartext secret config) is in .gitignore,"
	echo "    however if you copy or rename it, take care not to git commit/push it. "
	echo "  ********************************************************************************"

test-connect: # Connect to evon OpenVPN server, impersonating an endpoint server using config in this directory
	sudo mkdir -p /etc/openvpn
	sudo [ -e /etc/openvpn/evon.uuid ] || \
		sudo bash --login -c 'echo -e "endpoint-$(uuidgen)\nnull" > /etc/openvpn/evon.uuid'
	[ -e openvpn_secrets.conf ] || \
		make decrypt
	[ -e openvpn_proxy.conf.inc ] || ln -s openvpn_proxy.conf openvpn_proxy.conf.inc
	[ -e openvpn_secrets.conf.inc ] || ln -s openvpn_secrets.conf openvpn_secrets.conf.inc
	sudo openvpn openvpn_client.conf

