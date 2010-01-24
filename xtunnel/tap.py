import datetime
import fcntl
import logging
import os
import pwd
import struct
import subprocess
import threading


TUNSETIFF = 0x400454ca
TUNSETOWNER = TUNSETIFF + 2
IFF_TUN   = 0x0001
IFF_TAP   = 0x0002
IFF_NO_PI = 0x1000

address_file = '/sys/devices/virtual/net/tap7/address'


class TAPDevice(threading.Thread):

    def __init__(self, config, node=None):
        threading.Thread.__init__(self)
        self.node = node
        self.ip = config['ip']

        self.tap = open('/dev/net/tun', 'r+b')
        ifr = struct.pack('16sH', 'tap7', IFF_TAP|IFF_NO_PI)
        ifs = fcntl.ioctl(self.tap, TUNSETIFF, ifr)
        fcntl.ioctl(self.tap, TUNSETOWNER,
                pwd.getpwnam(config['user']).pw_uid)

        command = 'ifconfig tap7 %s netmask %s up' % (
                self.ip, config['mask'])
        subprocess.check_call(command, shell=True)

        self.mac = filter(lambda x: x != ':',
                open(address_file).read().strip())

    def write(self, bytes_):
        os.write(self.tap.fileno(), bytes_)

    def fileno(self):
        return self.tap

    def run(self):
        while True:
            # logging.debug('%s - tun' % datetime.datetime.now())
            bytes_ = os.read(self.tap.fileno(), 2000)
            self.node.handle_frame(Frame(bytes_))



rmap = {'\x08\x00': 'IP',
        '\x08\x06': 'ARP'}


class Frame(object):

    def __init__(self, bytes_):
        self.bytes_ = bytes_

        self.target = bytes_[:6]
        self.source = bytes_[6:12]
        self.type_ = bytes_[12:14]
        self.payload = bytes_[14:]

    def __repr__(self):
        return self.bytes_

    def get_type(self):
        return rmap.get(self.type_)

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
