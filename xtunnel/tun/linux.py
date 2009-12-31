import fcntl
import os
import struct
import threading


_TUNSETIFF = 0x400454ca
_IFF_TUN   = 0x0001
_IFF_NO_PI = 0x1000
_IFF_MODE  = _IFF_TUN | _IFF_NO_PI


class TunDevice(threading.Thread):

    def __init__(self, tun_name, writer=None):
        threading.Thread.__init__(self)
        self.writer = writer

        self.tun = open('/dev/net/tun', 'r+b')
        ifr = struct.pack('16sH', tun_name, _IFF_MODE)
        ifs = fcntl.ioctl(self.tun, _TUNSETIFF, ifr)

    def write(self, message):
        os.write(self.tun.fileno(), message)

    def run(self):
        while True:
            message = os.read(self.tun.fileno(), 2000)
            self.writer.write(message)
