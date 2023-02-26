.SILENT:

help: # Show this help
	@echo Make targets:
	@egrep -h ":\s+# " $(MAKEFILE_LIST) | \
	  sed -e 's/# //; s/^/    /' | \
	  column -s: -t

deploy: # deploy Evon Selfhosted Shim
	cp evonshim.service /usr/lib/systemd/system
	systemctl daemon-reload
	systemctl start evonshim

