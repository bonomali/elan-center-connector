PACKAGE-NAME := elan-center-connector
PACKAGE-DESC := Easy LAN Agent
PACKAGE-DEPENDS := python3, python3-mako, python3-django, elan-agent, ca-certificates

include packaging.mk

.PHONY: install
install: core-python center-connection

.PHONY: core-python center-connection
core-python: elan/*.py
	install -d ${DESTDIR}${ORIGIN_PREFIX}/lib/python/elan
	install -m 644 -t ${DESTDIR}${ORIGIN_PREFIX}/lib/python/elan elan/*.py

.PHONY: center-connection
center-connection: bin/axon_websocket_proxy.py bin/axon_mapper.py bin/rule_fetcher.py axon.nginx axon.mosquitto
	install -d ${DESTDIR}${ORIGIN_PREFIX}/bin
	install bin/axon_websocket_proxy.py ${DESTDIR}${ORIGIN_PREFIX}/bin/axon-websocket-proxy
	install bin/axon_mapper.py ${DESTDIR}${ORIGIN_PREFIX}/bin/axon-mapper
	install bin/rule_fetcher.py ${DESTDIR}${ORIGIN_PREFIX}/bin/rule-fetcher
	install -d ${DESTDIR}/etc/nginx/sites-enabled
	ln -s ../sites-available/axon ${DESTDIR}/etc/nginx/sites-enabled/
	install -d ${DESTDIR}${ORIGIN_PREFIX}/elan-center
	install -m 644 axon.nginx ${DESTDIR}${ORIGIN_PREFIX}/elan-center/
	install -m 644 axon.mosquitto ${DESTDIR}${ORIGIN_PREFIX}/elan-center/
