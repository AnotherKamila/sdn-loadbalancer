#!/usr/bin/env python

from __future__ import print_function
from twisted.internet.protocol import Protocol, Factory
from twisted.internet          import defer, task
from twisted.spread            import pb
import attr
import sys

from myutils import remote_all_the_things, raise_all_exceptions_on_client

from twisted.internet import reactor
defer.setDebugging(True)

class ConnCounterProtocol(Protocol, object):
    def connectionMade(self):
        self.factory.conn_counter.count += 1
        self.factory.conn_counter.load  += 1.0/self.factory.load_factor

    def dataReceived(self, data):
        self.transport.write(data)

    def connectionLost(self, reason):
        self.factory.conn_counter.load -= 1.0/self.factory.load_factor


class ConnCounter(pb.Root, object):
    def __init__(self, *args, **kwargs):
        self.count = 0
        self.load  = 0.3
        self.load_samples = [0]*20

    def sample_load(self):
        self.load_samples.pop(0)
        self.load_samples.append(self.load)

    @raise_all_exceptions_on_client
    def remote_get_conn_count(self):
        return self.count

    @raise_all_exceptions_on_client
    def remote_get_load(self):
        return sum(self.load_samples)/len(self.load_samples)

    @raise_all_exceptions_on_client
    def remote_reset_conn_count(self):
        self.count = 0

def main():
    conn_counter = ConnCounter()

    path = sys.argv[1] if len(sys.argv) > 1 else '/tmp/p4crap-server.socket'
    reactor.listenUNIX(path, pb.PBServerFactory(conn_counter))

    serverport  =   int(sys.argv[2]) if len(sys.argv) > 2 else 8000
    load_factor = float(sys.argv[3]) if len(sys.argv) > 3 else 10
    f = Factory.forProtocol(ConnCounterProtocol)
    f.conn_counter = conn_counter
    f.load_factor  = load_factor
    reactor.listenTCP(serverport, f)
    load_sampler = task.LoopingCall(conn_counter.sample_load)
    load_sampler.start(0.5)

    reactor.run()

if __name__ == '__main__':
    main()
