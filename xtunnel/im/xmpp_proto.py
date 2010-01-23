import base64
import datetime
import logging
import threading
import xmpp


class XMPPClient(threading.Thread):

    def __init__(self, config, writer=None):
        threading.Thread.__init__(self)
        self.jid = xmpp.protocol.JID(config['account'])
        self.password = config['password']
        self.peer = config['peer']
        self.writer = writer

        self.client = xmpp.Client(self.jid.getDomain(), debug=[])
        self.peer_online = False

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
        self.client.RegisterHandler('message', self.__message)
        self.client.RegisterHandler('presence', self.__presence)
        self.client.sendInitPresence()
        return True

    def __message(self, conn, message):
        type_ = message.getType()
        peer = message.getFrom().getStripped()
        if type_ == 'normal' and peer == self.peer:
            self.writer.write(base64.b64decode(message.getBody()))

    def __presence(self, conn, presence):
        type_ = presence.getType()
        peer = xmpp.protocol.JID(presence.getFrom()).getStripped()
        if peer != self.peer:
            return
        if not type_:
            self.peer_online = True
        elif type_ == 'unavailable':
            self.peer_online = False
        else:
            print 'Not support to be that.'

    def write(self, message):
        if self.peer_online:
            message = base64.b64encode(message)
            m = xmpp.protocol.Message(to=self.peer, body=message, typ='normal')
            self.client.send(m)

    def fileno(self):
        return self.client.Connection._sock

    def run(self):
        while True:
            self.client.Process(1)
