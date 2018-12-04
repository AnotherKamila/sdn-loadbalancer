import pytest_twisted as pt
import pytest
import os
from twisted.internet import defer, task
from twisted.spread import pb
from twisted.internet import reactor
import itertools

from controller.l4_loadbalancer import LoadBalancer

import time
from myutils.testhelpers import run_cmd, kill_with_children

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
        yield task.deferLater(reactor, 1, (lambda: None))
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
def test_equal_balancing_inprocess(remote_module, p4run):
    NUM_CONNS = 1000
    TOLERANCE = 0.8

    pools = {
        "10.0.1.1:8000": ["h1:8001", "h2:8002", "h3:8003"],
        "10.0.1.1:7000": ["h1:7000"]
    }

    # create pools
    lb = yield LoadBalancer.get_initialised('s1', topology_db_file=p4run.topo_path)
    for vip, dips in pools.items():
        handle = yield lb.add_pool(vip)
        for dip in dips:
            yield lb.add_dip(handle, dip)

    # run the servers
    servers = {}  # vip => [server remote]
    for vip, dips in pools.items():
        servers[vip] = []
        server_ds = []
        for dip in dips:
            dhost, dport = hostport(dip)
            server_ds.append(remote_module('myutils.server', dport, host=dhost))
        server_conns = yield defer.DeferredList(server_ds)
        for success, conn in server_conns:
            assert success
            servers[vip].append(conn)

    # run the client
    client = yield remote_module('myutils.client', host='h4')
    for vip in pools:
        vip, vport = hostport(vip)
        yield client.callRemote('make_connections', vip, vport, count=NUM_CONNS)

    # check the servers' connection counts
    for vip, dips in pools.items():
        expected_conns = TOLERANCE * NUM_CONNS/len(dips)
        for server in servers[vip]:
            num_conns = yield server.callRemote('get_conn_count')
            assert num_conns >= expected_conns

def test_weighted_balancing(remote_module, p4run):
    pass