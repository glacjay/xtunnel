import datetime
import fcntl
import logging
import os
import pwd
import struct
import subprocess
import threading


_TUNSETIFF = 0x400454ca
_TUNSETOWNER = _TUNSETIFF + 2
_IFF_TUN   = 0x0001
_IFF_NO_PI = 0x1000
_IFF_MODE  = _IFF_TUN | _IFF_NO_PI


class TUNDevice(threading.Thread):

    def __init__(self, config, writer=None):
        threading.Thread.__init__(self)
        self.writer = writer

        self.tun = open('/dev/net/tun', 'r+b')
        ifr = struct.pack('16sH', config['name'], _IFF_MODE)
        ifs = fcntl.ioctl(self.tun, _TUNSETIFF, ifr)
        fcntl.ioctl(self.tun, _TUNSETOWNER,
                pwd.getpwnam(config['user']).pw_uid)

        command = 'ifconfig %s %s pointopoint %s up' % (
                config['name'], config['local'], config['remote'])
        subprocess.check_call(command, shell=True)

    def write(self, message):
        os.write(self.tun.fileno(), message)

    def fileno(self):
        return self.tun

    def run(self):
        while True:
            # logging.debug('%s - tun' % datetime.datetime.now())
            message = os.read(self.tun.fileno(), 2000)
            self.writer.write(message)
