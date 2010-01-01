#!/usr/bin/env python

import ConfigParser
import os
import sys
from xtunnel.tun.linux import TunDevice
from xtunnel.xmpp_ import XmppClient


def usage():
    print '''\
Usage: %s config

config  -- configuration file.
''' % sys.argv[0]
    sys.exit(0)

def main():
    if len(sys.argv) == 2 and sys.argv[1] in ['--help', '-h']:
        usage()

    config = ConfigParser.ConfigParser()
    config.read(os.path.expanduser('~/.xtunnelrc'))
    if len(sys.argv) > 1:
        config.read(sys.argv[1])
    tun_name = config.get('tun', 'name')
    account = config.get('im', 'account')
    password = config.get('im', 'password')
    peer = config.get('im', 'peer')

    tun = TunDevice(tun_name)
    xmpp = XmppClient(account, password, peer, tun)
    if not xmpp.connect():
        sys.exit(1)
    tun.writer = xmpp
    tun.start()
    xmpp.start()


if __name__ == '__main__':
    main()
