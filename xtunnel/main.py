#!/usr/bin/env python


import ConfigParser
import daemon
import datetime
import grp
import lockfile
import logging
import os
import pwd
import signal
import sys
import time

from tun.linux import TUNDevice
from xmpp_ import XMPPClient


logging.basicConfig(filename='/tmp/xtunnel.log', level=logging.DEBUG)


def usage():
    print '''\
Usage: %s [config]

config -- configuration file (ConfigParser format).
''' % sys.argv[0]
    sys.exit(0)

config = None
tun = None
im = None

def init():
    global config, tun, im

    if len(sys.argv) == 2 and sys.argv[1] in ['--help', '-h']:
        usage()

    config = ConfigParser.ConfigParser()
    config.read('/etc/xtunnel.conf')
    if len(sys.argv) > 1:
        config.read(sys.argv[1])

    logging.basicConfig(
            filename=config.get('config', 'log_path'),
            level=logging.DEBUG)

    tun = TUNDevice(dict(config.items('tun')))
    im = XMPPClient(dict(config.items('im')), tun)
    if not im.connect():
        sys.exit(1)
    tun.writer = im

def run():
    global tun, im
    tun.start()
    im.start()
    while True:
        time.sleep(1)


def main():
    global config, tun, im
    init()

    context = daemon.DaemonContext(
        files_preserve=[tun.fileno(), im.fileno()],
        # chroot_directory=config.get('config', 'chroot_path'),  # can't find /dev/null
        umask=0o002,
        pidfile=lockfile.FileLock(config.get('config', 'pid_path')),
        uid=pwd.getpwnam(config.get('config', 'user')).pw_uid,
        gid=grp.getgrnam(config.get('config', 'group')).gr_gid,
        stderr=sys.stderr if config.getboolean('config', 'debug') else None,
    )
    context.signal_map = {
        signal.SIGTERM: 'terminate'
    }

    with context:
        run()


if __name__ == '__main__':
    main()
