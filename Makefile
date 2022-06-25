.SILENT:
INVENTORY_FILE := inventory/hosts
TARGET := all

help: # Show this help
	@echo Make targets:
	@egrep -h ":\s+# " $(MAKEFILE_LIST) | \
	  sed -e 's/# //; s/^/    /' | \
	  column -s: -t

deploy: # deploy
	cd ansible && ansible-playbook evon-hub.yml
