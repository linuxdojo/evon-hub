.SILENT:

help: # Show this help
	@echo Make targets:
	@egrep -h ":\s+# " $(MAKEFILE_LIST) | \
	  sed -e 's/# //; s/^/    /' | \
	  column -s: -t

uninstall: # remove Evon Selfhosted Shim
	systemctl stop evonshim.service >/dev/null 2>&1 || :
	systemctl disable evonshim.service >/dev/null 2>&1 || :
	rm /usr/lib/systemd/system/evonshim.service >/dev/null 2>&1 || :

install: # install and start Evon Selfhosted Shim
	cp evonshim.service /usr/lib/systemd/system
	systemctl daemon-reload
	systemctl start evonshim.service
	systemctl enable evonshim.service

deploy: # deploy Evon Selfhosted Shim to localhost (root required)
	make uninstall
	make install
	# wait for socket to bind
	count=5; while true; do netstat -taupen | grep -qE '169.254.169.254:80.*LISTEN' && break; sleep 1; count=$$((count-1)); [ $$count -lt 1 ] && exit 1; done
	echo Evon selfhosted shim deployed.
