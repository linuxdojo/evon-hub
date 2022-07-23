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
	cd ansible && tar -zcf /tmp/evon_hub.tar.gz --exclude .gitignore --exclude .git --exclude .env --exclude requirements.txt .
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
	echo Wrote package file: $(OUTFILE)

publish: # publish package to AWS S3
	echo #TODO

