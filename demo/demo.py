#!/usr/bin/env python

from __future__ import print_function

from p4utils.utils.topology import Topology
from twisted.internet import defer, task
from myutils import all_results
from myutils.twisted_utils import sleep
from myutils.remote_utils import remote_module, kill_all_my_children
from controller.l4_loadbalancer import LoadLoadBalancer
from datetime import datetime

from twisted.internet import stdio
from twisted.protocols import basic
import os

class WaitForLines(basic.LineReceiver):
    delimiter = os.linesep

    def reset(self):
        self.line_received = defer.Deferred()

    def connectionMade(self):
        self.reset()

    def lineReceived(self, line):
        callback = self.line_received.callback
        self.reset()
        callback(line)


def setup_graph(server_IPs, lb):
    servers = [s for ip,s in sorted(server_IPs.items())]

    with open('./data.tsv', 'w') as f: pass  # the easiest way to truncate it :D
    demo_start = datetime.now()

    @defer.inlineCallbacks
    def update_graph():
        weights = [lb.get_weight(ip,p) for (ip,p) in server_IPs.keys()]
        loads   = yield all_results([server.callRemote('get_load')       for server in servers])
        conns   = yield all_results([server.callRemote('get_conn_count') for server in servers])
        now     = (datetime.now() - demo_start).total_seconds()

        data = [now]+weights+loads+conns
        with open('./data.tsv', 'a') as f:
            f.write('{}\n'.format('\t'.join([str(x) for x in data])))
            f.flush()

    graph_loop = task.LoopingCall(update_graph)
    graph_loop.start(0.5)


@defer.inlineCallbacks
def demo(reactor):
    lines = WaitForLines()
    stdio.StandardIO(lines)

    ##### Preparation ################################################################

    # These are our servers.
    server_hosts = [
        # host, port, num CPUs
        ('h1', 9000, 1),
        ('h1', 9001, 2),
        ('h2', 9002, 4),
        ('h3', 9003, 6),
    ]

    # Run the server and client programs and get a "remote control" to them.
    servers = yield all_results([
        remote_module('myutils.server', port, ncpus, host=host)
        for host, port, ncpus in server_hosts
    ])
    clients = yield all_results([
        remote_module('myutils.client', host='h3'),
        remote_module('myutils.client', host='h4'),
    ])

    # Build an (ip, port) => server remote dict to use later.
    topo = Topology('./topology.db')
    server_IPs = {
        (topo.get_host_ip(h), p): remote
        for (h, p, _), remote in zip(server_hosts, servers)
    }

    # Run my load balancer controller and teach it how to get load from the
    # servers.
    # In real life I could be e.g. SSHing into the servers, or using my
    # monitoring infrastructure.
    lb = yield LoadLoadBalancer.get_initialised(
        's1',
        get_load=lambda ip, p: server_IPs[(ip, p)].callRemote('get_load')
    )

    # Create a server pool on the loadbalancer.
    pool_handle = yield lb.add_pool('10.0.0.1', 8000)
    for ip, port in server_IPs.keys():
        yield lb.add_dip(pool_handle, ip, port)
    yield lb.commit()


    ##### Now the fun begins #########################################################

    setup_graph(server_IPs, lb)

    print()
    print('--------------------- press Enter to continue ---------------------------')
    yield lines.line_received
    print()

    print()
    print('-------------------------- starting demo --------------------------------')
    print()

    @defer.inlineCallbacks
    def client0():
        """Client 0 will send long-running requests: closes after 10 seconds."""
        print('client0 running')
        yield clients[0].callRemote('start_echo_clients', '10.0.0.1', 8000, count=5)
        reactor.callLater(10, clients[0].callRemote, 'close_all_connections')

    @defer.inlineCallbacks
    def client1():
        print('client1 running')
        """Client 1 will send bursts of short connections (2s)."""
        yield clients[1].callRemote('start_echo_clients', '10.0.0.1', 8000, count=20)
        reactor.callLater(2, clients[1].callRemote, 'close_all_connections')

    # Run client0 every 13 seconds.
    client0_loop = task.LoopingCall(client0)
    client0_loop.start(13)

    # Run client1 every 4 seconds.
    client1_loop = task.LoopingCall(client1)
    client1_loop.start(4)


if __name__ == '__main__':
    try:
        from twisted.internet import reactor
        demo(reactor)
        reactor.run()
    finally:
        kill_all_my_children()
