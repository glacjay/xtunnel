#!/usr/bin/env python


import ConfigParser
import daemon
import grp
import os
import pidlockfile
import pwd
import signal
import sys
import time

from tun.linux import TUNDevice
from im.xmpp_proto import XMPPClient
from im.msn_proto import MSNClient


proto_map = {
    'xmpp' : XMPPClient,
    'msn'  : MSNClient,
}


config = ConfigParser.ConfigParser()
config.read('/etc/xtunnel.conf')
pidfile = pidlockfile.TimeoutPIDLockFile(config.get('config', 'pid_path'))


def check():
    if pidfile.is_stale():
        pidfile.break_lock()
    if pidfile.is_locked():
        print 'Maybe there is an instance running already?'
        sys.exit(1)

def init():
    global tun, im

    tun_config = dict(config.items('tun'))
    tun_config.update(user=config.get('config', 'user'))
    tun = TUNDevice(tun_config)

    try:
        proto = proto_map[config.get('im', 'protocol')]
    except KeyError:
        print 'Unsupported IM protocol "%s".' % config.get('im', 'protocol')
        sys.exit(1)
    im = proto(dict(config.items('im')), tun)
    tun.writer = im
    if not im.connect():
        sys.exit(1)

def run():
    tun.start()
    im.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        sys.exit(0)


def start():
    check()
    init()

    stderr = None
    if config.getboolean('config', 'debug'):
        stderr = sys.stderr
    context = daemon.DaemonContext(
            files_preserve=[tun.fileno(), im.fileno()],
            pidfile=pidfile,
            uid=pwd.getpwnam(config.get('config', 'user')).pw_uid,
            gid=grp.getgrnam(config.get('config', 'group')).gr_gid,
            stderr=stderr,
            signal_map={signal.SIGTERM: 'terminate'},
            )

    with context:
        run()

def stop():
    if not pidfile.is_locked():
        print 'There is no instance running.'
        sys.exit(1)
    if pidfile.is_stale():
        pidfile.break_lock()
    else:
        pid = pidfile.read_pid()
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            print 'Failed to terminate the instance.'
            sys.exit(1)

def restart():
    stop()
    start()

def stand():
    check()
    init()
    run()

def status():
    if pidfile.is_locked():
        print 'There is an instance running.'
    else:
        print 'There is no instance running.'

action_funcs = {
    'start'   : start,
    'stop'    : stop,
    'restart' : restart,
    'stand'   : stand,
    'status'  : status,
}

def do_action():
    action = sys.argv[1]
    if action not in action_funcs:
        print 'Unknown action: %s' % action
        sys.exit(1)
    action_funcs[action]()


def usage_exit():
    print '''Usage: %s start|stop|restart|stand|status''' % sys.argv[0]
    sys.exit(1)

def main():
    if len(sys.argv) > 1:
        do_action()
    else:
        usage_exit()


if __name__ == '__main__':
    main()
