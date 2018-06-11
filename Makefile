PACKAGE-NAME := elan-center-connector
PACKAGE-DESC := Easy LAN Agent
PACKAGE-DEPENDS := python3, python3-mako, python3-django, elan-agent, ca-certificates, postfix

ELAN_PREFIX := /elan-agent
PYTHON_PIPENVFILES := embedded/python

.PHONY: build
build:
	#

include packaging.mk

.PHONY: install
install: core-python center-connection

.PHONY: core-python center-connection
core-python: elan/*.py core-pylib
	install -d ${DESTDIR}${ELAN_PREFIX}/lib/python/elan
	install -m 644 -t ${DESTDIR}${ELAN_PREFIX}/lib/python/elan elan/*.py

.PHONY: center-connection
center-connection: bin/axon_websocket_proxy.py bin/axon_mapper.py bin/rule_fetcher.py axon.nginx axon.mosquitto guest-request-email.html guest-request-email.txt
	install -d ${DESTDIR}${ELAN_PREFIX}/bin
	install bin/axon_websocket_proxy.py ${DESTDIR}${ELAN_PREFIX}/bin/axon-websocket-proxy
	install bin/axon_mapper.py ${DESTDIR}${ELAN_PREFIX}/bin/axon-mapper
	install bin/rule_fetcher.py ${DESTDIR}${ELAN_PREFIX}/bin/rule-fetcher
	install -d ${DESTDIR}${ELAN_PREFIX}/elan-center
	install -m 644 axon.nginx ${DESTDIR}${ELAN_PREFIX}/elan-center/
	install -m 644 axon.mosquitto ${DESTDIR}${ELAN_PREFIX}/elan-center/
	install -m 644 base-email.html ${DESTDIR}${ELAN_PREFIX}/elan-center/
	install -m 644 guest-request-email.html ${DESTDIR}${ELAN_PREFIX}/elan-center/
	install -m 644 guest-request-email.txt ${DESTDIR}${ELAN_PREFIX}/elan-center/

.PHONY: core-pylib
core-pylib: websockets
	install -d ${DESTDIR}${ELAN_PREFIX}/lib/python
	( cd ${PYTHON_PIPENVFILES}; \
		find $^ -type d -exec install -d ${DESTDIR}${ELAN_PREFIX}/lib/python/{} \;; \
		find $^ -type f -not -name \*.pyc -exec cp -Pp {} ${DESTDIR}${ELAN_PREFIX}/lib/python/{} \;; \
		find $^ -type l -exec cp -pP {} ${DESTDIR}${ELAN_PREFIX}/lib/python/{} \; \
	)

.PHONY: websockets

.PHONY: embedded-python
embedded-python:
	rm -rf ${PYTHON_PIPENVFILES}
	mkdir -p ${PYTHON_PIPENVFILES}
	cp Pipfile* ${PYTHON_PIPENVFILES}/
	cd ${PYTHON_PIPENVFILES}; pipenv --three install --ignore-pipfile; \
		cp -rp $$(pipenv --venv)/lib/python3.6/site-packages/*/ .; \
		rm -rf *.dist-info easy_install.py pip  pkg_resources  setuptools wheel; \
		find . -name \*.pyc -o -name __pycache__ -print0 | xargs -0 -I {} /bin/rm -rf "{}" \;; \
		pipenv --rm

deb: embedded-python

