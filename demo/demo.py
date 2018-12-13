#!/usr/bin/env python

from __future__ import print_function

from p4utils.utils.topology import Topology
from twisted.internet import defer, task
from myutils import all_results
from myutils.twisted_utils import sleep
from myutils.remote_utils import remote_module, kill_all_my_children
from controller.l4_loadbalancer import LoadLoadBalancer

@defer.inlineCallbacks
def demo(reactor):

    ##### Preparation ################################################################

    # These are our servers.
    server_hosts = [
        # host, port, num CPUs
        ('h1', 9000, 1),
        ('h1', 9001, 1),
        ('h2', 9002, 2),
        ('h3', 9003, 4),
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

    # Run client0 every 12 seconds.
    client0_loop = task.LoopingCall(client0)
    client0_loop.start(12)

    # Run client1 every 3 seconds.
    client1_loop = task.LoopingCall(client1)
    client1_loop.start(3)


    ##### and don't forget to make pretty graphs :-) #################################

    @defer.inlineCallbacks
    def update_graph():
        weights = [lb.get_weight(ip,p) for (ip,p) in server_IPs.keys()]
        loads   = yield all_results([server.callRemote('get_load')       for server in servers])
        conns   = yield all_results([server.callRemote('get_conn_count') for server in servers])
        print('!!!', loads)
        print('!!!', weights)
        print('!!!', conns)

    graph_loop = task.LoopingCall(update_graph)
    graph_loop.start(1.0)


if __name__ == '__main__':
    try:
        from twisted.internet import reactor
        demo(reactor)
        reactor.run()
    finally:
        kill_all_my_children()
