from django.conf import settings
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from mako.lookup import TemplateLookup
from mako.template import Template
import datetime
import time

from elan import utils, session, device
from elan.neuron import Dendrite, Synapse, RequestTimeout, RequestError
from uuid import uuid4
import smtplib
import threading

CC_IPv4 = ['87.98.150.15']  # Control center IPs to be used in NGINX conf: indeed, when no resolver available, NGINX fails if we use fqdn
CC_IPv6 = ['2001:41d0:2:ba47::1:11']

ACCOUNT_ID_PATH = 'account:id'
AGENT_ID_PATH = 'agent:id'
AGENT_UUID_PATH = 'agent:uuid'
AGENT_LOCATION_PATH = 'agent:location'

synapse = Synapse()

# Must be called before import of make_password
settings.configure()


class AxonMapper:

    def __init__(self):
        self.dendrite = Dendrite()

    def run(self):
        configure_axon()

        self.dendrite.provide('register', self.register)
        self.dendrite.provide('check-connectivity', self.check_connectivity)
        self.dendrite.provide('guest-request', self.guest_request)
        self.dendrite.subscribe('notify-knowledge', self.notify_knowledge)

        self.dendrite.wait_complete()

    def notify_knowledge(self, info):
        if 'sessions' in info:
            session.notify_current_sessions()
        if 'hostnames' in info:
            device.notify_known_hostnames()
        if 'fingerprints' in info:
            device.notify_known_fingerprints()

    def guest_request(self, request):
        response = self.dendrite.call('elan-center/guest-request', request)

        if response['sponsor_email'] or response['fixed_recipients']:
            # send mail
            lookup = TemplateLookup(['/elan-agent/elan-center'])
            html_template = Template(filename='/elan-agent/elan-center/guest-request-email.html', lookup=lookup)
            text_template = Template(filename='/elan-agent/elan-center/guest-request-email.txt', lookup=lookup)
            html = html_template.render(**response)
            text = text_template.render(**response)

            if not response['sponsor_email']:
                recipients = response['fixed_recipients']
                bcc_recipients = []
            else:
                recipients = [response['sponsor_email']]
                bcc_recipients = response['fixed_recipients']

            send_mail(recipients=recipients,
                        bcc_recipients=bcc_recipients,
                        html=html,
                        text=text,
                        mail_subject='Guest Request for Network Access'
            )

        return response

    def check_connectivity(self, data=None):
        # check elan-center connectivity
        try:
            connected = bool(int(self.dendrite.get('$SYS/broker/connection/{uuid}/state'.format(uuid=synapse.get(AGENT_UUID_PATH)))))
        except RequestTimeout:
            connected = False

        if connected:
            return {'status': 'connected'}
        raise RequestError('Connection to ELAN Center down')

    def register(self, data):
        # settings.configure must have been called before this imort
        from django.contrib.auth.hashers  import make_password

        # check elan-center connectivity
        self.check_connectivity()

        if not data:
            return {'status': 'available'}

        data['interfaces'] = sorted(utils.physical_ifaces())

        result = self.dendrite.call('elan-center/register', data)  # raises RequestError if registration fails

        # store this admin in conf (should be overridien once Axon correctly configured)
        self.dendrite.publish_conf('administrator', [dict(login=data['login'], password=make_password(data['password']))])

        synapse.set(ACCOUNT_ID_PATH, result['account'])
        synapse.set(AGENT_ID_PATH, result['id'])
        synapse.set(AGENT_UUID_PATH, result['uuid'])

        # delay configuration so that caller has time to receive response...
        def delayed_action():
            configure_axon()
            # wait axon really started.
            time.sleep(5.0)
            session.notify_current_sessions()
            device.notify_known_hostnames()
            device.notify_known_fingerprints()

        t = threading.Timer(3.0, delayed_action)
        t.start()

        return {'status': 'registered'}


def configure_axon(reload=True):
    uuid = synapse.get(AGENT_UUID_PATH)
    agent_id = synapse.get(AGENT_ID_PATH)
    account_id = synapse.get(ACCOUNT_ID_PATH)

    if not uuid:
        uuid = str(uuid4())
        synapse.set(AGENT_UUID_PATH, uuid)

    axon_template = Template(filename="/elan-agent/elan-center/axon.nginx")
    with open ("/etc/nginx/sites-enabled/axon", "w") as axon_file:
        axon_file.write(axon_template.render(
                                  uuid=uuid,
                                  cc_ipv4=CC_IPv4,
                                  cc_ipv6=CC_IPv6,
                       ))

    # Reload Nginx
    if reload:
        utils.reload_service('nginx')

    mosquitto_template = Template(filename="/elan-agent/elan-center/axon.mosquitto")
    with open ("/etc/mosquitto/conf.d/axon.conf", "w") as mosquitto_file:
        mosquitto_file.write(mosquitto_template.render(
                                  uuid=uuid,
                                  agent_id=agent_id,
                                  account_id=account_id
                            )
        )

    # Reload Nginx
    if reload:
        utils.restart_service('mosquitto')


def send_mail(recipients, cc_recipients=None, bcc_recipients=None, text='', html=None, sender='', mail_subject='', mail_from='"ELAN Agent"', embedded=None):
    '''
    Sends a mail to recipients, cc_recipients and bcc_recipients using text or html or both as alternate.
    embedded can be added using embedded as a dict of {cid: path} where cid is the embedded object cid used in html to refer to it (<img src="cid:<cid>">) and path is the path to the file
    '''
    # TODO: files can be added using images as a dict of {filename: path} where filename is the name displayed in the mail and path is the path to the file
    if cc_recipients is None:
        cc_recipients = []
    if bcc_recipients is None:
        bcc_recipients = []
    if embedded is None:
        embedded = {}

    if not isinstance(recipients, list):
        recipients = [recipients]
    if not isinstance(cc_recipients, list):
        cc_recipients = [cc_recipients]
    if not isinstance(bcc_recipients, list):
        bcc_recipients = [bcc_recipients]

    if embedded:
        html_msg = MIMEMultipart('related')
        html_msg.attach(MIMEText(html, 'html'))
        # Attach embedded
        for cid in embedded:
            file_path = embedded[cid]
            with open(file_path, 'rb') as fp:
                embedded_msg = MIMEImage(fp.read())
            html_msg.attach(embedded_msg)
    else:
        html_msg = MIMEText(html, 'html')

    if html and text:
        msg = MIMEMultipart('alternative')
        msg.attach(MIMEText(text, 'plain'))
        msg.attach(html_msg)  # Last is best and preferred according to RFC 2046
    elif html:
        msg = html_msg
    else:
        msg = MIMEText(text, 'plain')

    msg['From'] = mail_from
    for recipient in recipients:
        msg['To'] = recipient  # some magic here...
    for recipient in cc_recipients:
        msg['CC'] = recipient  # some magic here...
    msg['Subject'] = mail_subject

    s = smtplib.SMTP('localhost')

    s.sendmail(sender, recipients + cc_recipients + bcc_recipients, msg.as_string())
    s.quit()
