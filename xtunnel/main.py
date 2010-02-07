#!/usr/bin/env python


import base64
import ConfigParser
import daemon
import fcntl
import grp
import os
import pidlockfile
import pwd
import select
import signal
import socket
import struct
import subprocess
import sys
import time

from xmpp import Client
from xmpp.protocol import JID, Message, Presence


##################################################
# Utils
##################################################

class Frame(object):

    rmap = {'\x08\x00': 'IP',
            '\x08\x06': 'ARP'}

    def __init__(self, bytes_):
        self.bytes_ = bytes_

        self.target = bytes_[:6]
        self.source = bytes_[6:12]
        self.type_ = bytes_[12:14]
        self.payload = bytes_[14:]

    def __repr__(self):
        return self.bytes_

    def get_type(self):
        return self.rmap.get(self.type_)

    def get_target(self):
        return ''.join([('%02x' % ord(c)) for c in self.target])

    def get_arp_reply(self, hwaddr):
        self.target = ''.join(
                [chr(int(hwaddr[i*2:i*2+2], 16)) for i in range(len(hwaddr)/2)])
        result = '%s%s%s%s\x00\x02%s%s%s' % (
                self.source, self.target, self.type_, self.payload[:6],
                self.target, self.payload[24:28], self.payload[8:18])
        return result

    def get_required_ip(self):
        return '.'.join([str(ord(c)) for c in self.payload[24:28]])


class Host(object):

    def __init__(self, jid, ip, mac, eip=None, eport=None):
        self.jid = jid
        self.ip = ip
        self.mac = mac

        self.socket = None
        self.buffer = ''

        if eip:
            self.eip = eip
            self.eport = eport
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((eip, eport))
            len_ = len(str(client.jid))
            header = chr(len_ >> 8) + chr(len_ % 256)
            self.socket.send(header + str(client.jid))

    def set_link(self, socket_, buffer):
        self.socket = socket_
        self.buffer = buffer
        self.process()

    def fileno(self):
        if self.socket:
            return self.socket.fileno()
        else:
            return None

    def read(self):
        self.buffer += self.socket.recv(2000)
        self.process()

    def process(self):
        buf = self.buffer
        while True:
            if len(buf) < 2:
                break
            len_ = (ord(buf[0]) << 8) + ord(buf[1])
            if len(buf) < (2 + len_):
                break
            tap.write(buf[2:2+len_])
            frame = Frame(buf[2:2+len_])
            self.buffer = buf = self.buffer[2+len_:]

    def send_frame(self, frame):
        len_ = len(repr(frame))
        header = chr(len_ >> 8) + chr(len_ % 256)
        self.socket.send(header + repr(frame))


class HostManager(object):

    def __init__(self):
        self.jid_index = {}
        self.ip_index = {}
        self.mac_index = {}

    def by_jid(self, jid):
        return self.jid_index.get(jid)

    def by_ip(self, ip):
        return self.ip_index.get(ip)

    def by_mac(self, mac):
        return self.mac_index.get(mac)

    def add_host(self, host):
        self.jid_index[host.jid] = host
        self.ip_index[host.ip] = host
        self.mac_index[host.mac] = host

    def remove_host(self, jid):
        host = self.by_jid(jid)
        if host:
            del self.jid_index[jid]
            del self.ip_index[host.ip]
            del self.mac_index[host.mac]

    def handle_frame(self, frame):
        type_ = frame.get_type()

        if type_ == 'ARP':
            host = self.by_ip(frame.get_required_ip())
            if host:
                tap.write(frame.get_arp_reply(host.mac))

        elif type_ == 'IP':
            host = self.by_mac(frame.get_target())
            if host:
                if host.socket:
                    host.send_frame(frame)
                else:
                    client.send_frame(host.jid, frame)

        else:
            print '*** Unsupported Ethernet Frame Type: %s' % repr(frame.type_)

    def get_linked_hosts(self):
        return filter(lambda x: x.fileno(), self.jid_index.values())

##################################################
# Main Components
##################################################

class TAPDevice(object):

    TUNSETIFF = 0x400454ca
    TUNSETOWNER = TUNSETIFF + 2
    IFF_TUN   = 0x0001
    IFF_TAP   = 0x0002
    IFF_NO_PI = 0x1000

    address_file = '/sys/devices/virtual/net/tap7/address'

    def __init__(self):
        self.tap = open('/dev/net/tun', 'r+b')
        ifr = struct.pack('16sH', 'tap7', self.IFF_TAP|self.IFF_NO_PI)
        ifs = fcntl.ioctl(self.tap, self.TUNSETIFF, ifr)
        fcntl.ioctl(self.tap, self.TUNSETOWNER,
                pwd.getpwnam(config.get('config', 'user')).pw_uid)

        self.ip = config.get('tap', 'ip')
        command = 'ifconfig tap7 %s netmask %s up' % (
                self.ip, config.get('tap', 'mask'))
        subprocess.check_call(command, shell=True)

        self.mac = filter(lambda x: x != ':',
                open(self.address_file).read().strip())

    def read(self):
        hosts.handle_frame(Frame(os.read(self.tap.fileno(), 2000)))

    def write(self, bytes_):
        os.write(self.tap.fileno(), bytes_)

    def fileno(self):
        return self.tap.fileno()


class XMPPClient(object):

    def __init__(self):
        self.jid = JID(config.get('im', 'account'))
        self.jid.setResource('xtunnel')
        self.password = config.get('im', 'password')
        self.debug = config.get('config', 'debug') == 'true'

        self.status = 'Internal %s %s' % (tap.ip, tap.mac)
        if config.has_option('im', 'ip'):
            eip = config.get('im', 'ip')
            eport = int(config.get('im', 'port'))
            self.status = 'External %s %s %s %s' % (
                    tap.ip, tap.mac, eip, eport)

        self.reconnect()

    def connect(self):
        if not self.client.connect():
            print 'Failed to connect to the XMPP server.\nExiting...'
            return False

        auth = self.client.auth(self.jid.getNode(), self.password,
                self.jid.getResource())
        if not auth:
            print 'Failed to authenticate you.\nExiting...'
            return False

        self.client.RegisterHandler('message', self.handle_message)
        self.client.RegisterHandler('presence', self.handle_presence)
        self.client.send(Presence(status=self.status))

        return True

    def handle_presence(self, dispatcher, presence):
        type_ = presence.getType()
        jid = presence.getFrom()

        # When I login to the gtalk server, I have set my resource name to
        # 'xtunnel'.  But when I get the presence information, the server
        # will add some random characters after the resource string.
        # Following lines is to deal with this situation.
        if not jid.getResource().startswith('xtunnel'):
            return
        jid.setResource('xtunnel')

        if jid == self.jid:
            return          # TODO google kick me out?

        if type_ is None:   # available
            if presence.getStatus():
                info = presence.getStatus().split()
                if len(info) == 3 and info[0] == 'Internal':
                    [ip, mac] = info[1:]
                    host = Host(jid, ip, mac)
                    hosts.add_host(host)
                elif len(info) == 5 and info[0] == 'External':
                    [ip, mac, eip, eport] = info[1:]
                    if self.status.startswith('External') and tap.mac > mac:
                        host = Host(jid, ip, mac)
                    else:
                        host = Host(jid, ip, mac, eip, int(eport))
                    hosts.add_host(host)
        elif type_ == 'unavailable':
            hosts.remove_host(jid)

    def handle_message(self, dispatcher, message):
        if message.getType() != 'normal':
            return
        tap.write(base64.b64decode(message.getBody()))

    def read(self):
        try:
            self.client.Process()
        except:
            self.reconnect()

    def send_frame(self, jid, frame):
        message = base64.b64encode(repr(frame))
        try:
            self.client.send(Message(to=jid, typ='normal', body=message))
        except:
            self.reconnect()

    def fileno(self):
        return self.client.Connection._sock.fileno()

    def reconnect(self):
        try:
            time.sleep(7)
            self.client.disconnect()
        except:
            pass

        if self.debug:
            self.client = Client(self.jid.getDomain())
        else:
            self.client = Client(self.jid.getDomain(), debug=[])

        try:
            if not self.connect():
                self.reconnect()
        except:
            self.reconnect()


class Pending(object):

    def __init__(self, socket_):
        self.socket = socket_
        self.buffer = ''

    def fileno(self):
        return self.socket.fileno()

    def read(self):
        buf = self.socket.recv(2000)
        self.buffer = buf = self.buffer + buf
        if len(buf) >= 2:
            len_ = (ord(buf[0]) << 8) + ord(buf[1])
            if len(buf) >= (2 + len_):
                jid = JID(buf[2:2+len_])
                host = hosts.by_jid(jid)
                if host:
                    host.set_link(self.socket, buf[2+len_:])
                else:
                    self.socket.close()
                listener.close_link(self)


class Listener(object):

    def __init__(self):
        self.eip = config.get('im', 'ip')
        self.eport = config.getint('im', 'port')

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((self.eip, self.eport))
        self.socket.listen(10)      # TODO enough?

        self.pendings = []

    def fileno(self):
        return self.socket.fileno()

    def read(self):
        socket_, _ = self.socket.accept()
        self.pendings.append(Pending(socket_))

    def close_link(self, pending):
        self.pendings.remove(pending)


config = ConfigParser.ConfigParser()
config.read('/etc/xtunnel.conf')
pidfile = pidlockfile.TimeoutPIDLockFile(config.get('config', 'pid_path'))

tap = None
client = None
hosts = None
listener = None


def check():
    if pidfile.is_stale():
        pidfile.break_lock()
    if pidfile.is_locked():
        print 'Maybe there is an instance running already?'
        sys.exit(1)

def init():
    global tap, client, listener, hosts

    tap = TAPDevice()
    client = XMPPClient()
    hosts = HostManager()
    if config.has_option('im', 'ip'):
        listener = Listener()

def run():
    try:
        while True:
            input = [tap, client]
            input.extend(hosts.get_linked_hosts())
            if listener:
                input.append(listener)
                input.extend(listener.pendings)
            (input, _, _) = select.select(input, [], [], 3)
            for i in input:
                i.read()
    except KeyboardInterrupt:
        client.client.disconnect()


def start():
    check()
    init()

    files = [tap.fileno(), client.fileno()]
    if listener:
        files.append(listener.fileno())
    stderr = None
    if config.getboolean('config', 'debug'):
        stderr = sys.stderr
    context = daemon.DaemonContext(
            files_preserve=files,
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
    time.sleep(7)
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
