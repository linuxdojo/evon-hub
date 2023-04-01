.SILENT:
PACKAGE_NAME := evon-hub
EC2_USER := ec2-user
SELFHOSTED := false
#ENV := dev
#EC2_HOST := ec2-13-236-148-138.ap-southeast-2.compute.amazonaws.com
#DOMAIN_PREFIX := mycompany
#SUBNET_KEY := 111


help: # Show this help
	@echo Make targets:
	@egrep -h ":\s+# " $(MAKEFILE_LIST) | \
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
	# generate env
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
	cat support/package_motd | sed 's/__VERSION__/$(VER)/g' > /tmp/evon_hub_motd
	echo Wrote $$(ls -lah $(OUTFILE) | awk '{print $$5}') file: $(OUTFILE)

package-all: # make both AWS and Selfhosted packages
	make SELFHOSTED=false package
	make SELFHOSTED=true package


publish: # publish latest package to target ec2 host at file path /home/ec2-user/bin/evon-deploy
	if [ "$(SELFHOSTED)" == "true" ]; then echo "SELFHOSTED=true, aborting"; exit 1; fi
	make package
	echo "##### Publishing Package #####"
	ssh $(EC2_USER)@$(EC2_HOST) "mkdir -p bin"
	scp evon-hub_*.sh $(EC2_USER)@$(EC2_HOST):/home/ec2-user/bin
	ssh $(EC2_USER)@$(EC2_HOST) "rm -f bin/evon-deploy >/dev/null 2>&1 || :; mv bin/evon-hub_*.sh bin/evon-deploy; chmod +x bin/evon-deploy"
	echo Done.

publish-update: # deploy latest AWS and Selfhosted package to s3 where it will be available to all deployments via the local `evon --update` command and via the autoupdate scheduler
	if [ "$$(git rev-parse --abbrev-ref HEAD)" != "master" ] && [ "$(ENV)" != "dev" ]; then echo You must be in master branch to deploy an update package.; exit 1; fi
	make package-all
	echo "##### Publishing updated packages to S3 #####"
	aws s3 cp evon-hub-selfhosted_*.sh s3://evon-$(ENV)-hub-updates
	aws s3 cp evon-hub_*.sh s3://evon-$(ENV)-hub-updates
	echo Removing old updates...
	aws s3 ls s3://evon-$(ENV)-hub-updates | sort | head -n-6 | awk '{print $$NF}' | while read f; do aws s3 rm s3://evon-$(ENV)-hub-updates/$$f; done
	echo Done.

deploy-base: # setup newly-deployed target EC2 system to be ready for producing AMI. WARNING - the ssh pub key is deleted from ec2-user/known_hosts, you will NOT be able to ssh in, this is for creating an AMI only
	if [ "$(SELFHOSTED)" == "true" ]; then echo "SELFHOSTED=true, aborting"; exit 1; fi
	if [ "$$(git rev-parse --abbrev-ref HEAD)" != "master" ]; then echo You must be in master branch to deploy the base components.; exit 1; fi
	echo -n "WARNING: The taraget EC2 will not be reachable after this operation! Sleeping for 5 seconds, press ctrl-c to abort."
	while true; do echo -n .; count=$${count}.; sleep 1; [ "$$count" == "....." ] && break; done
	echo ""
	make publish
	echo "##### Deploying Base #####"
	scp /tmp/evon_hub_motd $(EC2_USER)@$(EC2_HOST):/tmp/motd
	ssh $(EC2_USER)@$(EC2_HOST) "sudo mv -f /tmp/motd /etc/motd"
	# run base build
	ssh $(EC2_USER)@$(EC2_HOST) "bash --login -c 'sudo /home/ec2-user/bin/evon-deploy -b'"
	# nuke the ssh pub key if prod, ready for AMI creation (to pass AWS MP security scan)
	[ "$(ENV)" == "prod" ] && ssh $(EC2_USER)@$(EC2_HOST) "bash --login -c 'sudo rm -f /home/ec2-user/.ssh/authorized_keys /root/.ssh/authorized_keys'" || :
	echo Done.

deploy-test: # DEV ONLY - convenience target to make package, publish and run installer on remote host
	if [ "$(SELFHOSTED)" == "true" ]; then echo "SELFHOSTED=true, aborting"; exit 1; fi
	make publish
	echo "##### Deploying #####"
	echo "Deploying to host: $(EC2_USER)@$(EC2_HOST)"
	ssh $(EC2_USER)@$(EC2_HOST) "bash --login -c 'sudo /home/ec2-user/bin/evon-deploy --domain-prefix $(DOMAIN_PREFIX) --subnet-key $(SUBNET_KEY)'"

deploy-quick: # DEV ONLY - convenience target to upload local non-Django project elements to remote dev ec2 instance (assumes root ssh with pub key auth has been setup)
	if [ "$(SELFHOSTED)" == "true" ]; then echo "SELFHOSTED=true, aborting"; exit 1; fi
	echo "##### Quick Deploying #####"
	make clean
	echo "Quick deploying..."
	rsync -avP \
		evon \
		ansible \
		hub \
		eapi \
		root@$(EC2_HOST):/opt/evon-hub/
	echo "Bounching evonapi service..."
	ssh root@$(EC2_HOST) "bash --login -c 'systemctl restart evonhub'"
	echo "Done."

shell: # launch an eapi shell as root
	sudo bash -c '. .env/bin/activate && eapi shell'

runserver: # run the dev server as root
	sudo bash -c '. .env/bin/activate && eapi runserver'

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

start-shim: # Start the evon_shim http service locally on TCP/8000
	uvicorn evon.selfhosted_shim.server:app --reload
