#!/usr/bin/env python

from __future__ import print_function
from twisted.internet.protocol import Protocol, Factory
from twisted.internet          import defer
from twisted.spread            import pb
import attr
import sys

from myutils import remote_all_the_things, raise_all_exceptions_on_client

from twisted.internet import reactor
defer.setDebugging(True)


class ConnCounter(pb.Root, object):
    def __init__(self, *args, **kwargs):
        self.count = 0
        self.load  = 0.3

    @raise_all_exceptions_on_client
    def remote_get_conn_count(self):
        return self.count

    @raise_all_exceptions_on_client
    def remote_get_load(self):
        return self.load

    def remote_reset_conn_count(self):
        self.count = 0

class ConnCounterProtocol(Protocol, object):
    def connectionMade(self):
        self.factory.conn_counter.count += 1
        self.factory.conn_counter.load  += 0.1
        self.transport.write('{}\n'.format(self.factory.conn_counter.count).encode('utf-8'))

    def connectionLost(self, reason):
        self.factory.conn_counter.load -= 0.1  # this doesn't simulate _average_ load, but immediate one, but whatever :D


def main():
    conn_counter = ConnCounter()

    path = sys.argv[1] if len(sys.argv) > 1 else '/tmp/p4crap-server.socket'
    reactor.listenUNIX(path, pb.PBServerFactory(conn_counter))

    serverport = int(sys.argv[2]) if len(sys.argv) > 2 else 8000
    f = Factory.forProtocol(ConnCounterProtocol)
    f.conn_counter = conn_counter
    reactor.listenTCP(serverport, f)

    reactor.run()

if __name__ == '__main__':
    main()
