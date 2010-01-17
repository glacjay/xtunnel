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
        self.client.RegisterHandler('message', self._process)
        self.client.sendInitPresence()
        return True

    def _process(self, conn, event):
        type_ = event.getType()
        peer = event.getFrom().getStripped()
        if type_ == 'chat' and peer == self.peer:
            self.writer.write(base64.b64decode(event.getBody()))

    def write(self, message):
        message = base64.b64encode(message)
        m = xmpp.protocol.Message(to=self.peer, body=message, typ='chat')
        self.client.send(m)

    def fileno(self):
        return self.client.Connection._sock

    def run(self):
        while True:
            # logging.debug('%s - xmpp' % datetime.datetime.now())
            self.client.Process(1)
