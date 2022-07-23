.SILENT:
INVENTORY_FILE := inventory/hosts
TARGET := all

help: # Show this help
	@echo Make targets:
	@egrep -h ":\s+# " $(MAKEFILE_LIST) | \
	  sed -e 's/# //; s/^/    /' | \
	  column -s: -t

package: # produce package artefact ready for publishing
	tar -zcf evon.tgz --exclude .gitignore --exclude .git --exclude .env --exclude requirements.txt ansible/
	echo #TODO

publish: # publish package to AWS S3
	echo #TODO

