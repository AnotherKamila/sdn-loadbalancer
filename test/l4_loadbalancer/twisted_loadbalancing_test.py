import pytest_twisted as pt
import pytest
import os
from twisted.internet import defer
from twisted.spread import pb
from twisted.internet import reactor
import itertools

from controller.l4_loadbalancer import LoadBalancer

import time
from myutils.testhelpers import run_cmd

def hostport(s):
    return s.split(':')

@pytest.fixture()
def process(request):
    ps = []
    def run(cmd, host=None, background=True):
        ps.append(run_cmd(cmd, host, background=True))
    yield run

    for p in ps:
        p.terminate()

def python_m(module, *args):
    return ['pipenv', 'run', 'python', '-m', module] + list(args)

def sock(*args):
    return '/tmp/p4crap-{}.socket'.format('-'.join(str(a)) for a in args)

@pytest.fixture()
def remote_module(request, process):
    sock_counter = itertools.count(1)
    def run(module, *m_args, **p_kwargs):
        sock_name = sock(module, next(sock_counter))
        process(python_m(module, sock_name, *m_args), **p_kwargs)
        time.sleep(1)  # TODO
        conn = pb.PBClientFactory()
        reactor.connectUNIX(sock_name, conn)
        return conn.getRootObject()
    return run

@pt.inlineCallbacks
def test_inprocess_server_client(remote_module):
    server = yield remote_module('myutils.server')
    client = yield remote_module('myutils.client')
    yield client.callRemote('make_connections', 'localhost', 8000, count=47)
    num_conns = yield server.callRemote('get_conn_count')
    assert num_conns == 47

@pt.inlineCallbacks
def test_equal_balancing_inprocess(p4run, process):
    NUM_CONNS = 1000
    TOLERANCE = 0.9

    pools = {
        "10.0.1.1:8000": ["h1:8001", "h2:8002", "h3:8003"],
        "10.0.1.1:7000": ["h1:7000"]
    }

    lb = yield LoadBalancer.get_initialised('s1')

    servers = {}
    for vip, dips in pools.items():
        servers[vip] = []
        vhost, vport = hostport(vip)
        handle = yield lb.add_pool(vip)
        for dip in dips:
            yield lb.add_dip(handle, dip)
            dhost, dport = hostport(dip)
            servers[vip].append(run_server(host=dhost, port=dport, wait_to_bind=False))
    time.sleep(2.5)  # give them time to bind

    for vip, dips in pools.items():
        vip, vport = hostport(vip)
        assert run_client(NUM_CONNS, vip, vport, host='h4') == 0

    for vip, dips in pools.items():
        s = servers[vip]
        assert get_conns_and_die(s) >= TOLERANCE*NUM_CONNS/len(dips)
