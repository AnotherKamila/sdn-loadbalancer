#!/usr/bin/env python

from __future__ import print_function

from twisted.internet import reactor, task, defer, address
from twisted.internet.protocol import ClientFactory, Protocol

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

@defer.inlineCallbacks
def main(reactor, num_conns, host='localhost', port=8000):
    factory = MultiConnectionFactory.forProtocol(NullClient, num_conns)
    for i in range(num_conns):
        delay = i*(1.0/CONN_RATE) if CONN_RATE > 0 else 0
        reactor.callLater(delay, reactor.connectTCP, host, port, factory)
    try:
        yield factory.done
    except Exception as e:
        print('{} connections failed'.format(factory.num_failed))
        raise e

if __name__ == '__main__':
    import sys
    num_conns = int(sys.argv[1])
    host, port = (sys.argv[2], sys.argv[3]) if len(sys.argv) >= 4 else ('localhost', 8000)
    task.react(main, [num_conns, host.encode('utf-8'), int(port)])
