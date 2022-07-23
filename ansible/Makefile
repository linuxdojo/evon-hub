.SILENT:
INVENTORY_FILE := inventory/hosts
TARGET := localhost

help: # Show this help
	@echo Make targets:
	@egrep -h ":\s+# " $(MAKEFILE_LIST) | \
	  sed -e 's/# //; s/^/    /' | \
	  column -s: -t

deps: # Install dependencies from ansible-galaxy (stored in requirements.yml)
	ansible-galaxy install --roles-path roles -r requirements.yml

test: # test local playbooks for validity
	find ./ -maxdepth 1 -name '*.yml' | grep -v requirements | xargs -n1 ansible-playbook -i $(INVENTORY_FILE) --syntax-check --list-tasks

deploy: # deploy
	ansible-playbook evon-hub.yml
