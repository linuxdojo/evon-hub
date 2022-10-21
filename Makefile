.SILENT:
PACKAGE_NAME := evon-hub
EC2_USER := ec2-user
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

package: # produce package artefact ready for publishing
	echo "##### Packaging #####"
	rm -f evon-hub_*.sh
	# generate env
	ENV=$(ENV) support/gen_env.py
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
	$(eval NAME=$(PACKAGE_NAME)-$(BRANCH))
	$(eval GITCOUNT=$(shell git rev-list HEAD --count))
	$(eval VER=$(shell cat version.txt).$(GITCOUNT))
	$(eval OUTFILE=$(PACKAGE_NAME)_$(VER).sh)
	# write final package
	cp support/package_template.sh $(OUTFILE)
	cat /tmp/evon_hub.tar.gz | base64 >> $(OUTFILE)
	# cleanup
	rm -f /tmp/evon_hub.tar.gz
	sed -i 's/__VERSION__/$(VER)/g' $(OUTFILE)
	$(eval EVON_DOMAIN_SUFFIX=$(shell cat evon/.evon_env | grep EVON_DOMAIN_SUFFIX | cut -d= -f2 ))
	sed -i 's/__EVON_DOMAIN_SUFFIX__/$(EVON_DOMAIN_SUFFIX)/g' $(OUTFILE)
	echo Wrote $$(ls -lah $(OUTFILE) | awk '{print $$5}') file: $(OUTFILE)

publish: # publish package
	echo "##### Publishing Package #####"
	scp evon-hub_*.sh  $(EC2_USER)@$(EC2_HOST):evon-hub_latest.sh
	# TODO publish to S3, create API endpoint to pull latest, make script to pull/update/manage versions.

deploy: # make package, publish and run installer on remote host
	make test
	make clean
	make package
	make publish
	echo "##### Deploying #####"
	echo "Deploying to host: $(EC2_USER)@$(EC2_HOST)"
	ssh $(EC2_USER)@$(EC2_HOST) "chmod +x evon-hub_latest.sh; bash --login -c 'sudo ./evon-hub_latest.sh --domain-prefix $(DOMAIN_PREFIX) --subnet-key $(SUBNET_KEY)'"

clean: # remove unneeded artefacts from repo
	echo "##### Cleaning Repo #####"
	$(eval USER=$(shell whoami))
	find . -user root | while read o; do sudo chown $(USER) "$$o"; done
	find . -not -path "./.env/*" | grep -E "(__pycache__|\.pyc|\.pyo$$)" | while read o; do rm -rf "$$o"; done

quick-deploy: # DEV ONLY - upload local non-Django project elements to remote dev ec2 instance (assumes root ssh with pub key auth has been setup)
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
