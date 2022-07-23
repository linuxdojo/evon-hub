.SILENT:
PACKAGE_NAME := evon-hub

help: # Show this help
	@echo Make targets:
	@egrep -h ":\s+# " $(MAKEFILE_LIST) | \
	  sed -e 's/# //; s/^/    /' | \
	  column -s: -t

package: # produce package artefact ready for publishing
	# create archive
	rm -f /tmp/evon_hub.tar.gz || :
	tar -zcf /tmp/evon_hub.tar.gz --exclude .gitignore --exclude .git --exclude .env ansible requirements.txt version.txt
	# Generate output package filename
	$(eval NAME=$(PACKAGE_NAME)-$(BRANCH))
	$(eval GITCOUNT=$(shell git rev-list HEAD --count))
	$(eval VER=$(shell cat version.txt).$(GITCOUNT))
	$(eval OUTFILE=$(PACKAGE_NAME)_$(VER).sh)
	# write final package
	cp package_template.sh $(OUTFILE)
	cat /tmp/evon_hub.tar.gz | base64 >> $(OUTFILE)
	# cleanup
	rm -f /tmp/evon_hub.tar.gz
	sed -i 's/__VERSION__/$(VER)/g' $(OUTFILE)
	echo Wrote package file: $(OUTFILE)

publish: # publish package to AWS S3
	# FIXME shortcut for dev only, make this publish to s3
	scp evon-hub_0.1.15.sh  ec2-user@ec2-13-236-148-138.ap-southeast-2.compute.amazonaws.com:; ssh ec2-user@ec2-13-236-148-138.ap-southeast-2.compute.amazonaws.com "chmod +x evon-hub*.sh"

deploy:
	make package
	make publish
