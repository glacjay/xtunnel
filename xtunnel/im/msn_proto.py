import base64
import msncb
import msnlib
import sys
import threading
import time


class MSNClient(threading.Thread):

    def __init__(self, config, writer=None):
        threading.Thread.__init__(self)
        self.m = msnlib.msnd()
        self.m.cb = msncb.cb()
        self.m.email = config['account']
        self.m.pwd = config['password']
        self.peer = config['peer']
        self.peer_online = False

        self.setup_callbacks()

    def setup_callbacks(self):
        for p in dir(self):
            if p.startswith('cb_'):
                setattr(self.m.cb, p[3:], getattr(self, p))

    def connect(self):
        try:
            self.m.login()
            self.m.sync()
            self.m.change_status('online')
            print 'Connecting succeeded.'
            return True
        except:
            print 'Failed to connect or authenticate.'
            return False

    def write(self, message):
        if self.peer_online:
            self.m.sendmsg(self.peer, base64.b64encode(message))

    def fileno(self):
        return self.m.fileno()

    def run(self):
        while True:
            self.m.read(self.m)
            self.m.sync()

    #
    # callbacks
    #
    def cb_fln(self, md, type, tid, params):
        email = tid
        print >> sys.stderr, '*** fln: %s: offline' % email

        if email == self.peer:
            self.peer_online = False

        msncb.cb_fln(md, type, tid, params)

    def cb_iln(self, md, type, tid, params):
        t = params.split(' ')
        status = msnlib.reverse_status[t[0]]
        email = t[1]
        print >> sys.stderr, '*** iln: %s: %s' % (email, status)

        msncb.cb_iln(md, type, tid, params)

    def cb_msg(self, md, type, tid, params, sbd):
        t = tid.split(' ')
        email = t[0]
        print >> sys.stderr, '*** msg: %s: %s' % (email, params)
        msncb.cb_msg(md, type, tid, params, sbd)

    def cb_nln(self, md, type, tid, params):
        status = msnlib.reverse_status[tid]
        t = params.split(' ')
        email = t[0]
        print >> sys.stderr, '*** nln: %s: %s' % (email, status)

        if email == self.peer:
            self.peer_online = True

        msncb.cb_nln(md, type, tid, params)

    def cb_rng(self, md, type, tid, params):
        t = params.split(' ')
        email = t[3]
        print >> sys.stderr, '*** rng: %s' % email

        if email == self.peer:
            msncb.cb_rng(md, type, tid, params)
