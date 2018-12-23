#!/usr/bin/env python

from twisted.internet.protocol import Protocol, Factory
from twisted.internet          import stdio, reactor, defer
from twisted.protocols         import basic
from twisted.web.server        import Site
from os                        import linesep

defer.setDebugging(True)

class ConnCounter(Protocol):
    def connectionMade(self):
        self.factory.conn_count += 1
        self.transport.write('{}\n'.format(self.factory.conn_count).encode('utf-8'))

class PrintConnCountAndDie(basic.LineReceiver):
    delimiter = linesep.encode("ascii")

    def __init__(self, conn_factory):
        self.conn_factory = conn_factory

    # @defer.inlineCallbacks
    def lineReceived(self, line):
        if line in [b'end', b'die']:
            # yield self.sendLine('{}\n'.format(self.conn_factory.conn_count).encode('utf-8'))
            print(self.conn_factory.conn_count)
            reactor.stop()
        else:
            self.sendLine(b':-(')

def start(port):
    f = Factory.forProtocol(ConnCounter)
    f.conn_count = 0
    stdio.StandardIO(PrintConnCountAndDie(f))
    reactor.listenTCP(port, f)
    reactor.run()

if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) >= 2 else 8000
    start(port)
