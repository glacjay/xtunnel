import base64
import datetime
import logging
from threading import Thread
from xmpp import Client
from xmpp.protocol import JID, Message, Presence


class Node(object):

    def __init__(self, jid, ip, mac):
        self.jid = jid
        self.ip = ip
        self.mac = mac

    def __str__(self):
        return '%s %s %s' % (self.jid, self.ip, self.mac)


class XMPPClient(Thread):

    def __init__(self, config, tap=None):
        Thread.__init__(self)

        self.jid = JID(config['account'])
        self.jid.setResource('xtunnel')
        self.password = config['password']
        self.tap = tap

        self.client = Client(self.jid.getDomain(), debug=[])

        self.by_ip = {}
        self.by_mac = {}
        self.by_jid = {}

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
        self.client.sendInitPresence()

        status = '%s %s' % (self.tap.ip, self.tap.mac)
        self.client.send(Presence(status=status))
        return True

    def handle_message(self, dispatcher, message):
        if message.getType() != 'normal':
            return
        self.tap.write(base64.b64decode(message.getBody()))

    def handle_presence(self, dispatcher, presence):
        type_ = presence.getType()
        jid = presence.getFrom()
        if jid == self.jid:
            return          # TODO google kick me out?
        if type_ is None:
            if presence.getStatus():
                ip, mac = presence.getStatus().split()
                node = Node(jid, ip, mac)
                self.by_jid[jid] = node
                self.by_ip[ip] = node
                self.by_mac[mac] = node
        elif type_ == 'unavailable':
            if jid in self.by_jid:
                node = self.by_jid[jid]
                self.by_ip.pop(node.ip)
                self.by_mac.pop(node.mac)
                self.by_jid.pop(jid)

    def handle_frame(self, frame):
        type_ = frame.get_type()
        if type_ == 'ARP':
            ip = frame.get_required_ip()
            if ip in self.by_ip:
                mac = self.by_ip[ip].mac
                response = frame.get_arp_reply(mac)
                self.tap.write(response)
        elif type_ == 'IP':
            target = frame.get_target()
            if target in self.by_mac:
                jid = self.by_mac[target].jid
                body = base64.b64encode(repr(frame))
                self.client.send(Message(to=jid, body=body, typ='normal'))

    def fileno(self):
        return self.client.Connection._sock

    def run(self):
        while True:
            self.client.Process(1)
