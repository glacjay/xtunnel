class Host(object):

    def __init__(self, jid, ip, mac):
        self.jid = jid
        self.ip = ip
        self.mac = mac


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
