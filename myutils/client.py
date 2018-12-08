#!/usr/bin/env python

from __future__ import print_function

import functools
from twisted.internet import reactor, task, defer, address
from twisted.internet.protocol import ClientFactory, Protocol
from twisted.spread            import pb
from warnings import warn
import sys
from myutils import raise_all_exceptions_on_client

CONN_RATE = 500  # connections per second
# actually switch cares about pps, starts dropping at 10kpps => lower if you start sending more stuff
DATA_RATE = 10  # bytes/s

defer.setDebugging(True)

class NullClient(Protocol):
    conn_seconds = 2.0

    def __init__(self):
        self.done = defer.Deferred()

    def connectionMade(self):
        reactor.callLater(self.conn_seconds, self.transport.loseConnection)

    def connectionLost(self, reason):
        self.done.callback(None)

    def connectionFailed(self, reason):
        self.done.errback(reason)

class EchoClient(Protocol):
    def __init__(self):
        self.num_dots_sent     = 0
        self.num_dots_received = 0
        self.loop = task.LoopingCall(self.send_dot)
        self.done = defer.Deferred()
        self.should_close = False

    def connectionMade(self):
        self.loop.start(interval=1.0/DATA_RATE).addErrback(self.done.errback)

    def send_dot(self):
        self.num_dots_sent += 1
        self.transport.write(b'.')

    def dataReceived(self, data):
        num_dots = data.count(b'.')
        self.num_dots_received += num_dots
        try:
            assert num_dots == len(data), "Received something that wasn't a dot!"
        except AssertionError as a:
            self.loop.stop()
            self.transport.loseConnection()
            self.done.errback(a)

    def close(self):
        if self.should_close: return  # already done
        self.should_close = True
        self.transport.loseConnection()

    def connectionLost(self, reason):
        self.should_close = True
        if self.loop.running: self.loop.stop()

        if self.should_close:
            # if I stopped the connection before I received a reply, that's
            # okay, so +-1 whatever
            if self.num_dots_sent - self.num_dots_received <= 1:
                self.done.callback(self.num_dots_received)
            else:
                self.done.errback(RuntimeError("sent {}, received {}".format(
                    self.num_dots_sent, self.num_dots_received)))
        else:
            if not self.done.called:
                self.done.errback(reason)

class MultiConnectionFactory(ClientFactory):
    def __init__(self, num_conns=1):
        self.num_conns = num_conns
        self.done = defer.Deferred()
        self.num_failed = 0
        self.protocol_instances = []

    def close_all(self):
        for p in self.protocol_instances:
            if hasattr(p, 'close'):
                p.close()
        defer.DeferredList([p.done for p in self.protocol_instances],fireOnOneErrback=True).chainDeferred(self.done)

    def buildProtocol(self, addr):
        p = ClientFactory.buildProtocol(self, addr)
        self.protocol_instances.append(p)
        return p


def check_port_is_int(f):
    @functools.wraps(f)
    def wrapped(ctx, host, port, *args, **kwargs):
        if not isinstance(port, (int, long)):
            warn('Received string port: {}. Possibly a bug?'.format(port))
        return f(ctx, host, port, *args, **kwargs)
    return wrapped

class ConnMaker(pb.Root, object):
    def _start_connections(self, host, port, count, conn_rate):
        ds = []
        for i in range(count):
            delay = i*(1.0/conn_rate) if conn_rate > 0 else 0
            ds.append(task.deferLater(reactor, delay, reactor.connectTCP, host, port, self.factory, timeout=10))
        return defer.DeferredList(ds, fireOnOneErrback=True)

    @raise_all_exceptions_on_client
    @check_port_is_int
    @defer.inlineCallbacks
    def remote_make_connections(self, host, port, count=1, conn_rate=CONN_RATE):
        self.factory = MultiConnectionFactory.forProtocol(NullClient, count)
        yield self._start_connections(host, port, count, conn_rate)
        # TODO wait for actually making the connections
        self.factory.close_all()
        yield self.factory.done  # wait for it to close

    @raise_all_exceptions_on_client
    @check_port_is_int
    def remote_start_echo_clients(self, host, port, count=1, conn_rate=CONN_RATE):
        self.factory = MultiConnectionFactory.forProtocol(EchoClient, count)
        return self._start_connections(host, port, count, conn_rate)

    @raise_all_exceptions_on_client
    def remote_close_all_connections(self):
        self.factory.close_all()
        return self.factory.done

def main():
    from twisted.internet import reactor
    path = sys.argv[1] if len(sys.argv) > 1 else '/tmp/p4crap-client.socket'
    reactor.listenUNIX(path, pb.PBServerFactory(ConnMaker()))
    reactor.run()

if __name__ == '__main__':
    main()
