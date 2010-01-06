#!/usr/bin/env python

import ConfigParser
import daemon
import datetime
import logging
import os
import sys
import time
from xtunnel.tun.linux import TunDevice
from xtunnel.xmpp_ import XmppClient


logging.basicConfig(filename='/tmp/xtunnel.log', level=logging.DEBUG)


def usage():
    print '''\
Usage: %s config

config  -- configuration file.
''' % sys.argv[0]
    sys.exit(0)

tun = None
im = None

def init():
    if len(sys.argv) == 2 and sys.argv[1] in ['--help', '-h']:
        usage()

    config = ConfigParser.ConfigParser()
    config.read(os.path.expanduser('~/.xtunnelrc'))
    if len(sys.argv) > 1:
        config.read(sys.argv[1])

    global tun, im
    tun = TunDevice(dict(config.items('tun')))
    im = XmppClient(dict(config.items('im')), tun)
    if not im.connect():
        sys.exit(1)
    tun.writer = im

def main():
    global tun, im
    tun.start()
    im.start()
    while True:
        logging.debug('%s - main' % datetime.datetime.now())
        time.sleep(1)
    tun.join()
    im.join()


if __name__ == '__main__':
    with daemon.DaemonContext():
        init()
        main()
