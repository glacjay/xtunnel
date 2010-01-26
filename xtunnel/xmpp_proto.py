import base64
import datetime
import logging
from threading import Thread
from xmpp import Client
from xmpp.protocol import JID, Message, Presence

from host import Host, HostManager


class XMPPClient(Thread):

    def __init__(self, config, tap=None):
        Thread.__init__(self)

        self.jid = JID(config['account'])
        self.jid.setResource('xtunnel')
        self.password = config['password']
        self.client = Client(self.jid.getDomain())

        self.tap = tap

        self.hosts = HostManager()

    def connect(self):
        self.conn = self.client.connect()
        if not self.conn:
            print 'Failed to connect to the XMPP server.\nExiting...'
            return False
        auth = self.client.auth(self.jid.getNode(), self.password,
                self.jid.getResource())
        if not auth:
            print 'Failed to authenticate you.\nExiting...'
            return False

        self.client.RegisterHandler('message', self.handle_message)
        self.client.RegisterHandler('presence', self.handle_presence)

        status = 'Internal %s %s' % (self.tap.ip, self.tap.mac)
        self.client.send(Presence(status=status))

        return True

    def handle_presence(self, dispatcher, presence):
        type_ = presence.getType()
        jid = presence.getFrom()

        if jid == self.jid:
            return          # TODO google kick me out?

        if type_ is None:   # available
            if presence.getStatus():
                info = presence.getStatus().split()
                if len(info) == 3 and info[0] == 'Internal':
                    [ip, mac] = info[1:3]
                    host = Host(jid, ip, mac)
                    self.hosts.add_host(host)
        elif type_ == 'unavailable':
            self.hosts.remove(jid)

    def handle_message(self, dispatcher, message):
        if message.getType() != 'normal':
            return
        self.tap.write(base64.b64decode(message.getBody()))

    def handle_frame(self, frame):
        type_ = frame.get_type()

        if type_ == 'ARP':
            host = self.hosts.by_ip(frame.get_required_ip())
            if host:
                self.tap.write(frame.get_arp_reply(host.mac))

        elif type_ == 'IP':
            host = self.hosts.by_mac(frame.get_target())
            if host:
                body = base64.b64encode(repr(frame))
                self.client.send(Message(to=host.jid, body=body, typ='normal'))

    def fileno(self):
        return self.client.Connection._sock

    def run(self):
        while True:
            self.client.Process(1)
