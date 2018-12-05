from __future__ import print_function

import pytest_twisted as pt
import pytest
import os
from twisted.internet import defer, task
from twisted.spread import pb
from twisted.internet import reactor
from pprint import pprint
import itertools

from controller.l4_loadbalancer import LoadBalancer

import time
from myutils.testhelpers import run_cmd, kill_with_children
from myutils import all_results

def hostport(s):
    h, p = s.split(':')
    return h, int(p)

@pytest.fixture()
def process(request):
    ps = []
    def run(cmd, host=None, background=True):
        ps.append((run_cmd(cmd, host, background=True), host))
    yield run
    for p, host in ps:
        # cannot exit them with .terminate() if they're in mx :-(
        # p.terminate()
        assert kill_with_children(p) == 0

def python_m(module, *args):
    time.sleep(0.1) # pipenv run opens Pipfile in exclusive mode or something,
                    # and then it throws up when I run more of them
    return ['pipenv', 'run', 'python', '-m', module] + list(args)

def sock(*args):
    return '/tmp/p4crap-{}.socket'.format('-'.join(str(a) for a in args))

@pytest.fixture()
def remote_module(request, process):
    sock_counter = itertools.count(1)
    remotes = []

    @defer.inlineCallbacks
    def run(module, *m_args, **p_kwargs):
        sock_name = sock(module, next(sock_counter))
        process(python_m(module, sock_name, *m_args), **p_kwargs)
        yield task.deferLater(reactor, 2, (lambda: None))
        conn = pb.PBClientFactory()
        reactor.connectUNIX(sock_name, conn)
        obj = yield conn.getRootObject()
        remotes.append(obj)
        defer.returnValue(obj)

    return run


@pt.inlineCallbacks
def test_inprocess_server_client(remote_module):
    server = yield remote_module('myutils.server', 6000)
    client = yield remote_module('myutils.client')
    yield client.callRemote('make_connections', 'localhost', 6000, count=47)
    num_conns = yield server.callRemote('get_conn_count')
    assert num_conns == 47

@pt.inlineCallbacks
def test_add_dip(remote_module, p4run):
    print(' --------- prepare server, client, and loadbalancer ---------')
    client, server, lb = yield all_results([
        remote_module('myutils.client', host='h1'),
        remote_module('myutils.server', 8001, host='h2'),
        LoadBalancer.get_initialised('s1', topology_db_file=p4run.topo_path),
    ])
    print(' --------- set up the pool ---------')
    pool_h = yield lb.add_pool('10.0.0.1', 8000)
    yield lb.add_dip(pool_h, p4run.topo.get_host_ip('h2'), 8001)
    print(' --------- check that it worked ---------')
    yield client.callRemote('make_connections', '10.0.0.1', 8000, count=47)
    num_conns = yield server.callRemote('get_conn_count')
    assert num_conns == 47

@pytest.mark.xfail(reason="Not implemented yet")
@pt.inlineCallbacks
def test_rm_dip(remote_module, p4run):
    print(' --------- prepare server, client, and loadbalancer ---------')
    client, server, lb = yield all_results([
        remote_module('myutils.client', host='h1'),
        remote_module('myutils.server', 8001, host='h2'),
        LoadBalancer.get_initialised('s1', topology_db_file=p4run.topo_path),
    ])
    print(' --------- set up the pool ---------')
    pool_h = yield lb.add_pool('10.0.0.1', 8000)
    yield lb.add_dip(pool_h, p4run.topo.get_host_ip('h3'), 8001)  # will remove this later
    yield lb.add_dip(pool_h, p4run.topo.get_host_ip('h2'), 8001)
    yield lb.rm_dip(pool_h, 'h3:8001')  # tadaaa :D
    print(' --------- check that it worked ---------')
    yield client.callRemote('make_connections', '10.0.0.1', 8000, count=47)
    num_conns = yield server.callRemote('get_conn_count')
    assert num_conns == 47

@pt.inlineCallbacks
def test_equal_balancing(remote_module, p4run):
    NUM_CONNS = 1000
    TOLERANCE = 0.8

    pools = {
        ('10.0.0.1', 8000): [('h1', 8001), ('h2', 8002), ('h3', 8003)],
        ('10.0.0.1', 7000): [('h1', 7000)]
    }

    # create pools
    lb = yield LoadBalancer.get_initialised('s1', topology_db_file=p4run.topo_path)
    for vip, dips in pools.items():
        pool_h = yield lb.add_pool(*vip)
        for dip in dips:
            yield lb.add_dip(pool_h, p4run.topo.get_host_ip(dip[0]), dip[1])

    print(' ----- vips + inverse: -----')
    pprint(lb.vips.data)
    pprint(lb.vips_inverse.data)
    print(' ----- dips + inverse: -----')
    pprint(lb.dips.data)
    pprint(lb.dips_inverse.data)

    # run the servers
    servers = {}  # vip => [server remote]
    for vip, dips in pools.items():
        servers[vip] = []
        server_ds = []
        for dip in dips:
            dhost, dport = dip
            server_ds.append(remote_module('myutils.server', dport, host=dhost))
        servers[vip] = yield all_results(server_ds)

    # run the client
    client = yield remote_module('myutils.client', host='h4')
    for vip in pools:
        yield client.callRemote('make_connections', *vip, count=NUM_CONNS)

    # check the servers' connection counts
    for vip, dips in pools.items():
        expected_conns = TOLERANCE * NUM_CONNS/len(dips)
        for server in servers[vip]:
            num_conns = yield server.callRemote('get_conn_count')
            assert num_conns >= expected_conns

@pytest.mark.skip(reason="Weights not implemented yet")
@pt.inlineCallbacks
def test_weighted_balancing(remote_module, p4run):
    NUM_CONNS = 1000
    TOLERANCE = 0.8
    mypool = ('10.0.0.1', 8000)
    pool_ip, pool_port = mypool
    dips = [('h1', 8001), ('h2', 8002), ('h3', 8003)]
    client = yield remote_module('myutils.client', host='h4')

    # run the servers
    server_ds = []
    for dip in dips:
        dhost, dport = hostport(dip)
        server_ds.append(remote_module('myutils.server', dport, host=dhost))
    servers = yield all_results(server_ds)

    # create pool + set weights
    weights = []
    lb = yield LoadBalancer.get_initialised('s1', topology_db_file=p4run.topo_path)
    pool_handle = yield lb.add_pool(mypool)
    for i, dip in enumerate(dips):
        yield lb.add_dip(pool_handle, p4run.topo.get_host_ip(dip[0]), dip[1])
        weights.append(i*i + 1)
        yield lb.set_weight(*dip, weight=weights[i])

    # run the client
    yield client.callRemote('make_connections', pool_ip, pool_port, count=NUM_CONNS)

    # check the servers' connection counts
    expected_conns = [
        (float(weights[i])/sum(weights)) * NUM_CONNS * TOLERANCE
        for i in range(len(servers))
    ]
    for i, server in enumerate(servers):
        num_conns = yield server.callRemote('get_conn_count')
        print(' ========= ', num_conns, '/', expected_conns[i], ' =========== ')
        assert num_conns >= expected_conns[i]


@pytest.mark.skip(reason="Not done yet")
@pt.inlineCallbacks
def test_versioned_tables(remote_module, p4run):
    lb, client, server1, server2 = yield all_results([
        VersionedLoadBalancer.get_initialised('s1', topology_db_file=p4run.topo_path),
        remote_module('myutils.client', host='h3'),
        remote_module('myutils.server', 8001, host='h1'),
        remote_module('myutils.server', 8001, host='h2'),
    ])
    server1_ip, server2_ip = [p4run.topo.get_host_ip(h) for h in ('h1', 'h2')]

    lb = yield VersionedLoadBalancer.get_initialised('s1', topology_db_file=p4run.topo_path)
    pool_handle = yield lb.add_pool('10.0.0.1', 8000)

    yield lb.add_dip(pool_handle, server1_ip, 8001)
    lb.commit()
    yield lb.add_dip(pool_handle, server2_ip, 8001)  # don't commit this yet
    yield client.callRemote('make_connections', '10.0.0.1', 8000, count=47)
    num_conns = yield server1.callRemote('get_conn_count')
    assert num_conns == 47, "server1 should receive all, because server2 wasn't committed yet"

    yield lb.rm_dip(pool_handle, server1_ip, 8001)
    lb.commit()
    yield client.callRemote('make_connections', '10.0.0.1', 8000, count=47)
    num_conns = yield server2.callRemote('get_conn_count')
    assert num_conns == 47, ("server2 should receive all, because we committed "
                             "adding it and removing server1")
