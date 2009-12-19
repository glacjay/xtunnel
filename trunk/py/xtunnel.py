#!/usr/bin/env python

import sys


def usage():
    print '''\
Usage: %s if account peer

if      -- TUN interface's name, like 'tun0'
account -- the account used to logon XMPP server, like 'example@gmail.com'
peer    -- account used by the other host you want to connect to

If TUN interface does not exist, you must run me as root.
''' % sys.argv[0]
    sys.exit(0)

def main():
    if len(sys.argv) != 4:
        usage()

    tun = tun_alloc(sys.argv[1])

    from getpass import getpass
    password = getpass('Password for "%s": ' % sys.argv[2])
    xmpp = Xmpp(sys.argv[2], password, sys.argv[3], tun)
    if not xmpp.connect():
        sys.exit(1)

    main_loop(tun, xmpp)


import os, struct, fcntl

TUNSETIFF = 0x400454ca
IFF_TUN = 0x0001
IFF_NO_PI = 0x1000
IFF_MODE = IFF_TUN | IFF_NO_PI

def tun_alloc(tun_name):
    tun = open('/dev/net/tun', 'r+b')
    ifr = struct.pack('16sH', tun_name, IFF_MODE)
    ifs = fcntl.ioctl(tun, TUNSETIFF, ifr)
    return tun


import xmpp, base64

class Xmpp(object):

    def __init__(self, account, password, peer, tun):
        self.jid = xmpp.protocol.JID(account)
        self.client = xmpp.Client(self.jid.getDomain(), debug=[])
        self.password = password
        self.peer = peer
        self.tun = tun

    def connect(self):
        conn = self.client.connect()
        if not conn:
            print 'Connect to XMPP server failed.\nExit.'
            return False
        auth = self.client.auth(self.jid.getNode(), self.password,
                resource=self.jid.getResource())
        if not auth:
            print 'Auth to XMPP server failed.\nExit.'
            return False
        self.register_handlers()
        self.conn = conn
        self.client.sendInitPresence()
        return True

    @property
    def sock(self):
        return self.client.Connection._sock

    def register_handlers(self):
        self.client.RegisterHandler('message', self.process_xmpp)

    def process_xmpp(self, conn, event):
        typ = event.getType()
        peer = event.getFrom().getStripped()
        print "'%s' '%s' '%s'" % (typ, peer, self.peer)
        if typ in ['message', 'chat', None] and peer == self.peer:
            print 'receive message: %s' % event.getBody()
            os.write(self.tun.fileno(), base64.b64decode(event.getBody()))

    def send_message(self, message):
        m = xmpp.protocol.Message(to=self.peer, body=message, typ='chat')
        self.client.send(m)


from select import select

def main_loop(tun, xmpp):
    sock_list = { xmpp.sock: 'xmpp', tun: 'tun' }

    while True:
        (i, o, e) = select(sock_list.keys(), [], [], 1)
        for input in i:
            if sock_list[input] == 'xmpp':
                xmpp.client.Process(1)
            elif sock_list[input] == 'tun':
                process_tun(tun, xmpp)
            else:
                print 'Unknown socket type: %s' % repr(input)

def process_tun(tun, xmpp):
    package = os.read(tun.fileno(), 2000)
    message = base64.b64encode(package)
    print 'send out the message: %s' % message
    xmpp.send_message(message)


if __name__ == '__main__':
    main()
