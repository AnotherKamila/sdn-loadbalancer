from twisted.spread import pb
from twisted.internet import reactor, defer

def get_remote(sock):
    conn = pb.PBClientFactory()
    reactor.connectUNIX(sock, conn)
    return conn.getRootObject()


def get_client(sock='/tmp/p4crap-client.socket'):
    return get_remote(sock)
