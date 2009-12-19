#!/usr/bin/env python

import os, sys, struct, fcntl


def usage():
    print '''\
Usage: %s add if user
       %s del if

if   -- tun interface's name, like 'tun0'
user -- the number of your linux account, like 1000

This program must be run as root, anyway
''' % (sys.argv[0], sys.argv[0])
    sys.exit()

def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ['add', 'del']:
        usage()

    if sys.argv[1] == 'add':
        if len(sys.argv) != 4:
            usage()
        tun_add(sys.argv[2], int(sys.argv[3]))

    if sys.argv[1] == 'del':
        if len(sys.argv) != 3:
            usage()
        tun_del(sys.argv[2])


TUNSETIFF = 0x400454ca
TUNSETPERSIST = TUNSETIFF + 1
TUNSETOWNER = TUNSETIFF + 2
IFF_TUN = 0x0001
IFF_NO_PI = 0x1000
IFF_MODE = IFF_TUN | IFF_NO_PI

def tun_add(tun_name, user_id):
    tun = open('/dev/net/tun', 'rw')
    ifr = struct.pack('16sH', tun_name, IFF_MODE)
    ifs = fcntl.ioctl(tun, TUNSETIFF, ifr)
    fcntl.ioctl(tun, TUNSETPERSIST, 1)
    fcntl.ioctl(tun, TUNSETOWNER, user_id)

def tun_del(tun_name):
    tun = open('/dev/net/tun', 'rw')
    ifr = struct.pack('16sH', tun_name, IFF_MODE)
    ifs = fcntl.ioctl(tun, TUNSETIFF, ifr)
    fcntl.ioctl(tun, TUNSETPERSIST, 0)


if __name__ == '__main__':
    main()
