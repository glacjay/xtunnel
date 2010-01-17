import base64
import msnp
import threading
import time


class MessageHandler(msnp.ChatCallbacks):

    def __init__(self, client, chat):
        self.client = client
        self.peer = client.peer
        self.chat = chat

    def message_received(self, passport, display, text, charset):
        if passport == self.peer:
            self.client.writer.write(base64.b64decode(text))

    def friend_left(self, passport):
        self.client.chat = None


class MSNClient(threading.Thread, msnp.SessionCallbacks):

    def __init__(self, config, writer=None):
        threading.Thread.__init__(self)
        self.msn = msnp.Session(self)
        self.account = config['account']
        self.password = config['password']
        self.peer = config['peer']

    def connect(self):
        try:
            self.msn.login(self.account, self.password)
            self.msn.change_state(msnp.States.ONLINE)
            print 'Connecting succeeded.'
            return True
        except:
            print 'Failed to connect or authenticate.'
            return False

    def friend_online(self, state, passport, display):
        print '%s %s' % (passport, state)
        if state == msnp.States.ONLINE and passport == self.peer:
            self.msn.start_chat(self.peer)

    def friend_offline(self, passport):
        if passport == self.peer:
            self.chat = None

    def chat_started(self, chat):
        print 'chat started'
        self.chat = chat
        callbacks = MessageHandler(self, chat)
        chat.callbacks = callbacks

    def write(self, message):
        print 'write',
        if hasattr(self, 'chat'):
            self.chat.send_message(base64.b64encode(message))

    def fileno(self):
        return self.msn.conn.socket._sock

    def run(self):
        while True:
            self.msn.process(chats=True)
            time.sleep(200)
