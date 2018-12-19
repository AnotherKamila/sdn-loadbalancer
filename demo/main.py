#!/usr/bin/env python

from __future__ import print_function

from p4utils.utils.topology import Topology
from twisted.internet import defer, task, stdio
from twisted.python import failure
from myutils import all_results
from myutils.twisted_utils import sleep, WaitForLines
from myutils.remote_utils import remote_module, kill_all_my_children
from controller.l4_loadbalancer import MetricsLoadBalancer
from demo.utils import setup_graph

defer.setDebugging(True)
# failure.startDebugMode()

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
        ('h2', 9003, 8),
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

    # Teach my load balancer controller how to get load from the servers.
    # In real life I could be e.g. SSHing into the servers, or using my
    # monitoring infrastructure.
    def get_load(ip, port):
        return server_IPs[(ip, port)].callRemote('get_load', 20)
    def set_weights(loads):
        return [1.0/load for load in loads]

    # And start the controller.
    lb = yield MetricsLoadBalancer.get_initialised('s1',
                                                   get_metrics=get_load,
                                                   metrics_to_weights=set_weights)

    # Create a server pool on the loadbalancer.
    pool_handle = yield lb.add_pool('10.0.0.1', 8000)
    for ip, port in server_IPs.keys():
        yield lb.add_dip(pool_handle, ip, port)
    yield lb.commit()

    ##### Now the fun begins #########################################################

    setup_graph(server_IPs, lb, 10)

    print()
    print('--------------------- press Enter to start clients ----------------------')
    yield lines.line_received
    print()

    print()
    print('-------------------------- starting demo --------------------------------')
    print()

    @defer.inlineCallbacks
    def client0():
        """Client 0 will send long-running requests: closes after 10 seconds."""
        print('client0 running')
        yield clients[0].callRemote('start_echo_clients', '10.0.0.1', 8000, count=4)
        yield sleep(10)
        yield clients[0].callRemote('close_all_connections')

    @defer.inlineCallbacks
    def client1():
        """Client 1 will send bursts of short connections (2s)."""
        print('client1 running')
        yield clients[1].callRemote('start_echo_clients', '10.0.0.1', 8000, count=20)
        yield sleep(2)
        yield clients[1].callRemote('close_all_connections')

    # Run client0 every 13 seconds.
    client0_loop = task.LoopingCall(client0)
    client0_loop.start(13)

    # Run client1 every 4 seconds.
    client1_loop = task.LoopingCall(client1)
    client1_loop.start(3)


    print('---------------- press Enter to start adjusting weights ----------------')
    yield lines.line_received

    lb.start_loop()

if __name__ == '__main__':
    try:
        from twisted.internet import reactor
        demo(reactor)
        reactor.run()
    finally:
        kill_all_my_children()
