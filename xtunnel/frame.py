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
        return rmap[self.type_]

    def get_target(self):
        return [('%02x' % c) for c in self.target]

    def get_arp_reply(self, hwaddr):
        self.target = ''.join(
                [chr(int(hwaddr[i:i+2], 16)) for i in range(len(hwaddr)/2)])
        return '%s%s%s%s\x00\x02%s%s%s' % (
                self.source, self.target, self.type_, self.payload[:6],
                self.target, self.payload[24:28], self.payload[8:18])
