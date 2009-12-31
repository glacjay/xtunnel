#!/usr/bin/env python

from xtunnel.tun.linux import TunDevice
from xtunnel.xmpp_ import XmppClient
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

    from getpass import getpass
    password = getpass('Password for "%s": ' % sys.argv[2])

    tun = TunDevice(sys.argv[1])
    xmpp = XmppClient(sys.argv[2], password, sys.argv[3], tun)
    if not xmpp.connect():
        sys.exit(1)
    tun.writer = xmpp
    tun.start()
    xmpp.start()


if __name__ == '__main__':
    main()
