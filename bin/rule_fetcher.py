#!/usr/bin/env python3

import subprocess, os, sys
import yaml, re
from elan.utils import reload_service

file_h = open('/etc/suricata/suricata.yaml', 'r')

conf = yaml.load(file_h)
os.chdir(conf['default-rule-path'])

rules_updated = False

base_url = 'http://127.0.0.1:8000/ids-rules/'

for rule in conf['rule-files']:
    output = subprocess.check_output(['zsync', base_url + rule + '.zsync'], stderr=subprocess.STDOUT).decode()
    if re.search('downloading from', output):
        rules_updated = True

if rules_updated and (len(sys.argv) <= 1 or sys.argv[1] != '--no-rule-reload'):
    reload_service('elan-suricata')
