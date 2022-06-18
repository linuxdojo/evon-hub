.SILENT:
INVENTORY_FILE := inventory/hosts
SSH_PRIVATE_KEY := ~/.ssh/linuxdojo/id_rsa-evon
TARGET := all

help: # Show this help
	@echo Make targets:
	@egrep -h ":\s+# " $(MAKEFILE_LIST) | \
	  sed -e 's/# //; s/^/    /' | \
	  column -s: -t

deps: # Install dependencies from ansible-galaxy (stored in requirements.yml)
	ansible-galaxy install --roles-path roles -r requirements.yml

lshosts: # list all hosts in static hosts file
	sed '/\[.*/q' $(INVENTORY_FILE) | grep -v '^\s*[\[#].*' | sed '/^\s*$$/d' | sed 's/#.*//' | sed 's/ *$$//'

test: # test local playbooks for validity
	find ./ -maxdepth 1 -name '*.yml' | egrep -v 'requirements.yml|circle.yml' | xargs -n1 ansible-playbook -i ./hosts --syntax-check --list-tasks

ping: # ping target hosts in inventory, eg TARGET=all make ping, TARGET=dev make ping, TARGET=somehost.example.com make ping, etc
	ansible -i inventory $(TARGET) -m ping --private-key=$(SSH_PRIVATE_KEY)

deploy: # deploy
	ansible-playbook evon-hub.yml
