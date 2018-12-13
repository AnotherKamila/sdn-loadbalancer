#!/usr/bin/env python

from p4utils.utils.topology import Topology
from twisted.internet import defer, task
from myutils import all_results
from myutils.twisted_utils import sleep
from myutils.remote_utils import remote_module, kill_all_my_children
from controller.l4_loadbalancer import LoadBalancer

@defer.inlineCallbacks
def demo(reactor):
    server_hosts = [
        ('h1', 9000),
        ('h1', 9001),
        ('h2', 9002),
        ('h2', 9003),
    ]
    servers = yield all_results([
        remote_module('myutils.server', port, host=host)
        for host, port in server_hosts
    ])
    clients = yield all_results([
        remote_module('myutils.client', host='h3'),
        remote_module('myutils.client', host='h4'),
    ])
    lb = yield LoadBalancer.get_initialised('s1')

    topo = Topology('./topology.db')

    pool_handle = yield lb.add_pool('10.0.0.1', 8000)
    yield lb.add_dip(pool_handle, topo.get_host_ip('h1'), 9000)
    yield lb.commit()

    yield clients[0].callRemote('start_echo_clients', '10.0.0.1', 8000, count=5)
    yield sleep(1)

    yield lb.rm_dip(pool_handle, topo.get_host_ip('h1'), 9000)
    # roll over all the versions
    for i in range(10):
        yield lb.commit()

    yield clients[0].callRemote('close_all_connections')

    nconns = yield servers[0].callRemote('get_conn_count')
    assert nconns == 5


if __name__ == '__main__':
    try:
        from twisted.internet import reactor
        demo(reactor)
        reactor.run()
    finally:
        kill_all_my_children()
