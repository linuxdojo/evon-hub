.SILENT:
PACKAGE_NAME := evon-hub
TARGET_USER := ec2-user
SELFHOSTED := false
#ENV := dev
#TARGET_HOST := ec2-13-236-148-138.ap-southeast-2.compute.amazonaws.com
#DOMAIN_PREFIX := mycompany
#SUBNET_KEY := 111


help: # Show this help
	@echo Make targets:
	@grep -E -h ":\s+# " $(MAKEFILE_LIST) | \
	  sed -e 's/# //; s/^/    /' | \
	  column -s: -t

test: # Run unit tests
	echo "##### Running Tests #####"
	pytest evon/ eapi/ hub/
	flake8 --ignore=E501 evon/

clean: # remove unneeded artefacts from repo
	echo "##### Cleaning Repo #####"
	$(eval USER=$(shell whoami))
	find . -user root | while read o; do sudo chown $(USER) "$$o"; done
	find . -not -path "./.env/*" | grep -E "(__pycache__|\.pyc|\.pyo$$)" | while read o; do rm -rf "$$o"; done
	rm -f /tmp/evon_hub.tar.gz || :
	rm -rf _build || :


package: # produce package artefact ready for publishing
	make test
	make clean
	echo "##### Packaging #####"
	echo Checking AWS credentials...
	aws sts get-caller-identity 
	echo Removing old artefacts...
	if [ "$(SELFHOSTED)" == "true" ]; then \
		rm -f evon-hub-selfhosted_*.sh; \
	else \
		rm -f evon-hub_*.sh; \
	fi
	echo Packaging...
	# generate evon/.evon_env
	ENV=$(ENV) SELFHOSTED=$(SELFHOSTED) support/gen_env.py
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
		manage.py \
		requirements.txt \
		setup.py \
		version.txt
	# Generate output package filename
	$(eval GITCOUNT=$(shell git rev-list HEAD --count))
	$(eval VER=$(shell cat version.txt).$(GITCOUNT))
	$(eval OUTFILE=$(PACKAGE_NAME)$(shell [ "${SELFHOSTED}" == "true" ] && echo "-selfhosted" )_$(VER).sh)
	# write final package
	cp support/package_template.sh $(OUTFILE)
	cat /tmp/evon_hub.tar.gz | base64 >> $(OUTFILE)
	# cleanup
	rm -f /tmp/evon_hub.tar.gz
	# render installer package
	sed -i 's/__VERSION__/$(VER)/g' $(OUTFILE)
	sed -i "s/__EVON_DOMAIN_SUFFIX__/$$(cat evon/.evon_env | grep EVON_DOMAIN_SUFFIX | cut -d= -f2)/g" $(OUTFILE)
	sed -i 's/__SELFHOSTED__/$(SELFHOSTED)/g' $(OUTFILE)
	# render initial deploy motd
	mkdir _build
	cat support/package_motd | sed 's/__VERSION__/$(VER)/g' > _build/evon_hub_motd
	echo Wrote $$(ls -lah $(OUTFILE) | awk '{print $$5}') file: $(OUTFILE)

package-all: # make both AWS and Selfhosted packages
	make SELFHOSTED=false package
	make SELFHOSTED=true package

publish: # publish latest package to target host at file path ~/bin/evon-deploy
	make package
	echo "##### Publishing Package #####"
	ssh $(TARGET_USER)@$(TARGET_HOST) "mkdir -p bin"
	if [ "$(SELFHOSTED)" == "true" ]; then \
		scp evon-hub-selfhosted_*.sh $(TARGET_USER)@$(TARGET_HOST):bin/evon-deploy; \
	else \
		scp evon-hub_*.sh $(TARGET_USER)@$(TARGET_HOST):bin/evon-deploy; \
	fi
	ssh $(TARGET_USER)@$(TARGET_HOST) "chmod +x bin/evon-deploy"
	echo Done.

publish-update: # deploy latest AWS and Selfhosted package to s3 where it will be available to all deployments via the local `evon --update` command and via the autoupdate scheduler
	if [ "$$(git rev-parse --abbrev-ref HEAD)" != "master" ] && [ "$(ENV)" != "dev" ]; then echo You must be in master branch to deploy an update package.; exit 1; fi
	make package-all
	echo "##### Publishing updated packages to S3 #####"
	aws s3 cp evon-hub-selfhosted_*.sh s3://evon-$(ENV)-hub-updates
	aws s3 cp evon-hub_*.sh s3://evon-$(ENV)-hub-updates
	echo Removing old updates...
	aws s3api list-objects --bucket evon-$(ENV)-hub-updates --query 'sort_by(Contents, &LastModified)[].Key' --output text | sed 's/\s/\n/g' | head -n-6 | awk '{print $$NF}' | while read f; do aws s3 rm s3://evon-$(ENV)-hub-updates/$$f; done
	echo Done.

deploy-base: # setup newly-deployed target system to be ready for producing AMI or other image. WARNING - if not SELFHOSTED, the ssh pub key will be deleted from all known_host files and you will NOT be able to ssh in (for creating an AMI only)
	if [ "$$(git rev-parse --abbrev-ref HEAD)" != "master" ]; then echo You must be in master branch to deploy the base components.; exit 1; fi
	if [ "$(SELFHOSTED)" != "true" ]; then \
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
	# nuke the ssh pub key if deploying to prod EC2, ready for AMI creation (to pass AWS MP security scan)
	if [ "$(SELFHOSTED)" != "true" ]; then \
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

shell: # launch an eapi shell as root
	sudo bash -c '. .env/bin/activate && eapi shell'

runserver: # run the dev server as root
	sudo bash -c '. .env/bin/activate && eapi runserver 8001'

fwflush: # flush all Evon fw rules
	sudo bash -c '. .env/bin/activate && eapi fwctl --delete'

fwdelete: # flush all Evon fw rules
	sudo bash -c '. .env/bin/activate && eapi fwctl --delete-all'

fwinit: # initialise core Evon fw rules and chains
	sudo bash -c '. .env/bin/activate && eapi fwctl --init'

fwinitempty: # initialise all Evon fw rules and chains (including Rules and Policies)
	sudo bash -c '. .env/bin/activate && eapi fwctl --init-empty'

migrate: # run eapi migrate
	sudo bash -c '. .env/bin/activate && eapi migrate'

setup-local: # configure DB with fixtures for local development (ie if you want to 'make runserver')
	sudo bash -c '. .env/bin/activate && support/setup_local.sh'

get-version: # render the full current semantic version of evon-hub
	echo $$(cat version.txt).$$(git rev-list HEAD --count master)

start-shim: # Start the evon_shim http service locally on 169.254.169.254 on TCP/80
	sudo /usr/sbin/ip addr add 169.254.169.254/32 dev lo >/dev/null 2>&1 || :
	sudo bash -c '. .env/bin/activate && uvicorn evon.selfhosted_shim.server:app --reload --host 169.254.169.254 --port 80'
	sudo /usr/sbin/ip addr del 169.254.169.254/32 dev lo >/dev/null 2>&1 || :

freeze: # freeze pip deps and store into requirements.txt
	pip freeze | grep -v egg=evon  > requirements.txt
