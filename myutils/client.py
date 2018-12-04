#!/usr/bin/env python

from __future__ import print_function

from twisted.internet import reactor, task, defer, address
from twisted.internet.protocol import ClientFactory, Protocol
from twisted.spread            import pb
import sys
from myutils import raise_all_exceptions_on_client

CONN_RATE = 1000  # connections per second
# actually switch cares about pps, starts dropping at 10kpps => lower if you start sending more stuff

defer.setDebugging(True)

class NullClient(Protocol):
    conn_seconds = 2.0

    def connectionMade(self):
        reactor.callLater(self.conn_seconds, self.transport.loseConnection)

class MultiConnectionFactory(ClientFactory):
    def __init__(self, num_conns=1):
        self.num_conns = num_conns
        self.done = defer.Deferred()
        self.num_failed = 0

    def clientConnectionFailed(self, connector, reason):
        self.num_failed += 1
        if self.num_failed == 1:
            self.done.errback(reason)

    def clientConnectionLost(self, connector, reason):
        self.num_conns -= 1
        # print('.', end='')
        if self.num_conns == 0:
            self.done.callback(None)

class ConnMaker(pb.Root, object):
    @raise_all_exceptions_on_client
    @defer.inlineCallbacks
    def remote_make_connections(self, host, port, count=1):
        factory = MultiConnectionFactory.forProtocol(NullClient, count)
        for i in range(count):
            delay = i*(1.0/CONN_RATE) if CONN_RATE > 0 else 0
            reactor.callLater(delay, reactor.connectTCP, host, port, factory)
        try:
            yield factory.done
        except Exception as e:
            print('{} connections failed'.format(factory.num_failed))
            raise e

def main():
    from twisted.internet import reactor
    path = sys.argv[1] if len(sys.argv) > 1 else '/tmp/p4crap-client.socket'
    reactor.listenUNIX(path, pb.PBServerFactory(ConnMaker()))
    reactor.run()

if __name__ == '__main__':
    main()
