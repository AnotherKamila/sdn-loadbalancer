#!/usr/bin/env python

from __future__ import print_function
from twisted.internet.protocol import Protocol, Factory
from twisted.internet          import defer, task
from twisted.spread            import pb
import attr
import sys

from myutils import raise_all_exceptions_on_client

LOAD_AVERAGE_WINDOW    = 30   # seconds
LOAD_SAMPLING_INTERVAL = 0.2  # seconds

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
        self.load  = 0.1
        self.load_samples = [0.1]*int(float(LOAD_AVERAGE_WINDOW)/LOAD_SAMPLING_INTERVAL)

    def sample_load(self):
        self.load_samples.pop(0)
        self.load_samples.append(self.load)

    @raise_all_exceptions_on_client
    def remote_get_conn_count(self):
        return self.count

    @raise_all_exceptions_on_client
    def remote_get_load(self, average_over=10):
        num_samples = int(float(average_over)/LOAD_SAMPLING_INTERVAL)
        return sum(self.load_samples[-num_samples:])/num_samples

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
    load_sampler.start(LOAD_SAMPLING_INTERVAL)

    reactor.callWhenRunning(print, '[server] reactor running')
    reactor.run()

if __name__ == '__main__':
    main()
