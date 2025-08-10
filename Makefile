.SILENT:

### Evon Hub makefile.
#
# The purpose of this makefile is to:
#   - produce the installable Evon Hub executable, which is a single shell script. There are 3 flavours:
#   	- SaaS hosted on AWS Marketplace (paid service)
#   	- SaaS hosted on any EL8/9 host (paid service)
#   	- Free hosted on any EL8/9 host (free and open)
#   - publish and deploy the SaaS installers and their upgrades to their target hosts
#   - provide convenience functions for development such as starting the local web server
#
# Note that this software is released under the GNU AGPL Version 3. See file LICENSE.txt for more info.

## Main configuration

# The below env vars are defaults and can be overridden via the CLI when invoking make, eg:
#     HOSTED_MODE=standalone DOAIN_SUFFIX=mycompany.example.com  make package
# Run make without args to see help about available targets

# PACKAGE_NAME is used to render the name of distributable Evon Hub shell script installer package
PACKAGE_NAME := evon-hub

# HOSTED_MODE configures the target system on which the Hub will be deployed. It must be one of:
#   awsmp      - SaaS Hosted on AWS Marketplace for deployment as a Single Instance AMI product. Requires private AWS credentials in the Evon AWS account.
#   selfhosted - SaaS Hosted on any EL8/9 instance. Integrated with Evon API for payment and DNS management. Requires private AWS credentials in the Evon AWS account.
#   standalone - Free Hosted on any EL8/9 instance. Decoupled from all payment systems and provides the unrestricted, full featured product.
HOSTED_MODE := standalone

# The below vars are used for SaaS or development purposes
TARGET_USER := ec2-user
DOMAIN_PREFIX := mycompany
SUBNET_KEY := 111
#TARGET_HOST := ec2-13-236-148-138.ap-southeast-2.compute.amazonaws.com
#ENV := dev


help: # Show this help
	echo '   __| |  |    \ \  |'
	echo '   _|  \  | () |  \ | Hub'
	echo '  ___|  _/  ___/_| _| Makefile'
	echo '[ Elastic Virtual Overlay Network ]'
	echo ''
	echo 'Open `Makefile` for info regarding available environment variables.'
	echo ''
	echo Make targets:
	grep -E -h ":\s+# " $(MAKEFILE_LIST) | \
	  sed -e 's/# //; s/^/    /' | \
	  column -s: -t

test: # Run tests
	echo "##### Running Tests #####"
	pytest evon/ eapi/ hub/
	flake8 --ignore=E501 evon/
	cd ansible && make test

clean: # Remove unneeded artefacts from repo
	echo "##### Cleaning Repo #####"
	$(eval USER=$(shell whoami))
	find . -user root | while read o; do sudo chown $(USER) "$$o"; done
	find . -not -path "./.env/*" | grep -E "(__pycache__|\.pyc|\.pyo$$)" | while read o; do rm -rf "$$o"; done
	rm -f /tmp/evon_hub.tar.gz || :
	rm -rf _build || :

package: # Produce installer package artefact ready for publishing
	make test
	make clean
	echo "##### Packaging #####"
	if [ ! "${HOSTED_MODE}" == "standalone" ]; then \
		echo Checking AWS credentials...; \
		aws sts get-caller-identity; \
	fi
	echo Removing old artefacts...
	if [ "$(HOSTED_MODE)" == "awsmp" ]; then \
		rm -f evon-hub_*.sh; \
	elif [ "$(HOSTED_MODE)" == "selfhosted" ]; then \
		rm -f evon-hub-selfhosted_*.sh; \
	elif [ "$(HOSTED_MODE)" == "standalone" ]; then \
		rm -f evon-hub-standalone_*.sh; \
	else \
		echo "ERROR: HOSTED_MODE must be one of: awsmp, selfhosted, standalone"; \
		exit 1; \
	fi
	echo Packaging...
	# generate evon/.evon_env
	ENV=$(ENV) HOSTED_MODE=$(HOSTED_MODE) support/gen_env.py
	# create archive
	rm -f /tmp/evon_hub.tar.gz || :
	tar -zcf /tmp/evon_hub.tar.gz \
		--exclude '*.log' \
		--exclude '*.swp' \
		--exclude .gitignore \
		--exclude .git \
		--exclude .env \
		ansible \
		eapi \
		evon \
		hub \
		requirements.txt \
		pyproject.toml \
		version.txt \
		LICENSE.txt
	# Generate output package filename
	$(eval GITCOUNT=$(shell git rev-list HEAD --count))
	$(eval VER=$(shell cat version.txt).$(GITCOUNT))
	$(eval OUTFILE=$(PACKAGE_NAME)$(shell [ "${HOSTED_MODE}" != "awsmp" ] && echo "-${HOSTED_MODE}" )_$(VER).sh)
	# write final package
	cp support/package_template.sh $(OUTFILE)
	cat /tmp/evon_hub.tar.gz | base64 >> $(OUTFILE)
	# cleanup
	rm -f /tmp/evon_hub.tar.gz
	# render installer package
	sed -i 's/__VERSION__/$(VER)/g' $(OUTFILE)
	sed -i "s/__EVON_DOMAIN_SUFFIX__/$$(cat evon/.evon_env | grep EVON_DOMAIN_SUFFIX | cut -d= -f2)/g" $(OUTFILE)
	sed -i 's/__HOSTED_MODE__/$(HOSTED_MODE)/g' $(OUTFILE)
	# render initial deploy motd
	mkdir _build
	cat support/package_motd | sed 's/__VERSION__/$(VER)/g' > _build/evon_hub_motd
	echo Wrote $$(ls -lah $(OUTFILE) | awk '{print $$5}') file: $(OUTFILE)

package-all-saas: # Make both the AWS and Selfhosted SaaS installer packages
	make HOSTED_MODE=awsmp package
	make HOSTED_MODE=selfhosted package

package-oss: # Make the opensource standalone installer package
	make ENV=prod HOSTED_MODE=standalone package

package-all: # all packages
	make package-all-saas
	make package-oss

publish: # Publish latest SaaS package to target host at file path ~/bin/evon-deploy
	make package
	echo "##### Publishing Package #####"
	ssh $(TARGET_USER)@$(TARGET_HOST) "mkdir -p bin"
	if [ "$(HOSTED_MODE)" == "selfhosted" ]; then \
		scp evon-hub-selfhosted_*.sh $(TARGET_USER)@$(TARGET_HOST):bin/evon-deploy; \
	elif [ "$(HOSTED_MODE)" == "awsmp" ]; then \
		scp evon-hub_*.sh $(TARGET_USER)@$(TARGET_HOST):bin/evon-deploy; \
	else \
		echo "ERROR: only SaaS (awsmp or selfhosted) packages can be published."; \
		exit 1; \
	fi
	ssh $(TARGET_USER)@$(TARGET_HOST) "chmod +x bin/evon-deploy"
	echo Done.

publish-update: # Deploy latest SaaS (AWS and Selfhosted) package to S3 where it will be available to all deployments via the local `evon --update` command and via the autoupdate scheduler
	if ! echo "awsmp selfhosted" | grep -wq "$(HOSTED_MODE)"; then \
		echo "ERROR: only SaaS (awsmp or selfhosted) packages can be published."; \
		exit 1; \
	fi
	if [ "$$(git rev-parse --abbrev-ref HEAD)" != "master" ] && [ "$(ENV)" != "dev" ]; then echo You must be in master branch to deploy an update package.; exit 1; fi
	make package-all-saas
	echo "##### Publishing updated packages to S3 #####"
	aws s3 cp evon-hub-selfhosted_*.sh s3://evon-$(ENV)-hub-updates
	aws s3 cp evon-hub_*.sh s3://evon-$(ENV)-hub-updates
	echo Removing old updates...
	aws s3api list-objects --bucket evon-$(ENV)-hub-updates --query 'sort_by(Contents, &LastModified)[].Key' --output text | \
		sed 's/\s/\n/g' | \
		head -n-6 | \
		awk '{print $$NF}' | \
		while read f; do \
			aws s3 rm s3://evon-$(ENV)-hub-updates/$$f; \
		done
	echo Done.

deploy-base: # Setup fresh target system to be ready for producing AMI or VPS image for SaaS deployments. WARNING for "awsmp" mode - all authorized_keys files will be deleted and you will NOT be able to ssh in after this operation
	if ! echo "awsmp selfhosted" | grep -wq "$(HOSTED_MODE)"; then \
		echo "ERROR: only SaaS (awsmp or selfhosted) packages can be deployed."; \
		exit 1; \
	fi
	if [ "$$(git rev-parse --abbrev-ref HEAD)" != "master" ]; then echo You must be in master branch to deploy the base components.; exit 1; fi
	if [ "$(HOSTED_MODE)" == "awsmp" ]; then \
		echo -n "WARNING: The taraget EC2 will not be reachable after this operation! Sleeping for 5 seconds, press ctrl-c to abort."; \
		while true; do echo -n .; count=$${count}.; sleep 1; [ "$$count" == "....." ] && break; done; \
		echo ""; \
	fi
	make publish
	echo "##### Deploying Base #####"
	scp _build/evon_hub_motd $(TARGET_USER)@$(TARGET_HOST):/tmp/motd
	ssh $(TARGET_USER)@$(TARGET_HOST) "sudo mv -f /tmp/motd /etc/motd"
	# run base build
	ssh $(TARGET_USER)@$(TARGET_HOST) "bash --login -c 'sudo bin/evon-deploy -b'"
	# if not selfhosted, nuke the ssh pub key if deploying to prod EC2, ready for AMI creation (to pass AWS MP security scan), else setup the selfhosted instance
	if [ "$(HOSTED_MODE)" == "selfhosted" ]; then \
		ssh $(TARGET_USER)@$(TARGET_HOST) " \
			sudo sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/g' /etc/ssh/sshd_config; \
			sudo systemctl restart sshd; \
			sudo sed -i 's/^SELINUX=.*/SELINUX=disabled/g' /etc/selinux/config; \
			sudo sed -i \"s/$$(hostname)/evon-hub/g\" /etc/hosts; \
			sudo echo evoh-hub > /etc/hostname; \
			sudo hostname evon-hub; \
		"; \
	else \
		[ "$(ENV)" == "prod" ] && ssh $(TARGET_USER)@$(TARGET_HOST) "bash --login -c 'sudo rm -f /home/ec2-user/.ssh/authorized_keys /root/.ssh/authorized_keys'" || :; \
	fi
	echo Done.

deploy-test: # DEV ONLY - convenience target to make package, publish and run installer on target host
	make publish
	echo "##### Deploying #####"
	echo "Deploying to host: $(TARGET_USER)@$(TARGET_HOST)"
	ssh $(TARGET_USER)@$(TARGET_HOST) "bash --login -c 'sudo ~/bin/evon-deploy --domain-prefix $(DOMAIN_PREFIX) --subnet-key $(SUBNET_KEY)'"

deploy-quick: # DEV ONLY - convenience target to upload local non-Django project elements to remote dev EC2 instance (assumes root ssh with pub key auth has been setup)
	echo "##### Quick Deploying #####"
	make clean
	echo "Quick deploying..."
	rsync -avP \
		evon \
		ansible \
		hub \
		eapi \
		root@$(TARGET_HOST):/opt/evon-hub/
	echo "Bounching evonapi service..."
	ssh root@$(TARGET_HOST) "bash --login -c 'systemctl restart evonhub'"
	echo "Done."

shell: # Launch an eapi shell as root
	sudo bash -c '. .env/bin/activate && eapi shell'

runserver: # Run the dev server as root
	sudo bash -c '. .env/bin/activate && eapi runserver 8001'

fwflush: # Flush all Evon fw rules
	sudo bash -c '. .env/bin/activate && eapi fwctl --delete'

fwdelete: # Flush all Evon fw rules
	sudo bash -c '. .env/bin/activate && eapi fwctl --delete-all'

fwinit: # Initialise core Evon fw rules and chains
	sudo bash -c '. .env/bin/activate && eapi fwctl --init'

fwinitempty: # Initialise all Evon fw rules and chains (including Rules and Policies)
	sudo bash -c '. .env/bin/activate && eapi fwctl --init-empty'

migrate: # Run eapi migrate
	sudo bash -c '. .env/bin/activate && eapi migrate'

setup-local: # Configure DB with fixtures for local development (ie. if you want to 'make runserver')
	sudo bash -c '. .env/bin/activate && support/setup_local.sh'

get-version: # Render the full current semantic version of evon-hub
	echo $$(cat version.txt).$$(git rev-list HEAD --count master)

start-shim: # Start the evon_shim http service locally on 169.254.169.254 on TCP/80
	sudo /usr/sbin/ip addr add 169.254.169.254/32 dev lo >/dev/null 2>&1 || :
	sudo bash -c '. .env/bin/activate && uvicorn evon.selfhosted_shim.server:app --reload --host 169.254.169.254 --port 80'
	sudo /usr/sbin/ip addr del 169.254.169.254/32 dev lo >/dev/null 2>&1 || :

freeze: # Freeze pip deps and store into requirements.txt
	pip freeze | grep -v egg=evon  > requirements.txt
