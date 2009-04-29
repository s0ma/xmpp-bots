from twisted.internet               import reactor
from twisted.words.protocols.jabber import client, jid
from twisted.words.xish             import domish, xmlstream

class JabberBot(object):

    def __init__(self, jid, password, authorized, reactor=reactor, port=5222, resource="JabberBot"):
        self.jabberid   = jid
        self.password   = password
        self.authorized = authorized
        self.servername = jid[jid.find('@')+1:]
        self.port       = port
        self.resource   = resource

        self._jid           = None
        self._factory       = None
        self._reactor       = reactor
        self._resource      = None
        self._xmlstream     = None
        self.tryandregister = 1

    def run(self):
        self.__initFactory()
    
    def __repr__(self):
        return "<%s (%s)>" % (type(self).__name__, self.jabberid)
    
    def __initFactory(self):
        self._jid = jid.JID("%s/%s" % (self.jabberid, self.resource))
        self._factory = client.basicClientFactory(self._jid, self.password)
        
        self._factory.addBootstrap('//event/stream/authd', self._authd)
        
        self._reactor.connectTCP(self.servername, self.port, self._factory)
        self._reactor.run() 
    
    def _authd(self, xmlstream):
        if xmlstream:
            self._xmlstream = xmlstream
            
            # set it as online
            self._presence = domish.Element(('jabber:client', 'presence'))
            self._presence.addElement('status').addContent('Online')
            self._xmlstream.send(self._presence)

            self.__initOnline()
    
    def __initOnline(self):
        self._xmlstream.addObserver('/message', self._gotMessage)

    def _gotMessage(self, el):
        """called when a message is received"""
        from_id = el["from"]
        try:
            from_id, resource = from_id.split("/", 1)
        except:
            resource = None

        if from_id not in self.authorized:
            self.send_message(from_id, 'not authorized')
    
        body = None
        for e in el.elements():
            if e.name == "body":
                body = unicode(e.__str__())
                break

        if body is not None:
            self.recv_message(from_id, body)

    def recv_message(self, jid, message):
        args = message.strip().split()
        cmd  = 'do_' + args[0].lower()
        args = args[1:]

        if hasattr(self, cmd):
            reply = getattr(self, cmd)(*args)
        else:
            reply = self.handle_message(message)

        self.send_message(jid, reply)

    def handle_message(self, message):
        return 'unknown command'

    def send_message(self, to, body):
        message = domish.Element(('jabber:client','message'))
        message["to"] = jid.JID(to).full()
        message["from"] = self._jid.full()
        message["type"] = "chat"
        message.addElement("body", "jabber:client", body)
        
        self._xmlstream.send(message)
