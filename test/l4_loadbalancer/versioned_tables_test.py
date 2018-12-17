from __future__ import print_function, unicode_literals

import pytest_twisted as pt
import pytest
from twisted.internet import defer, reactor
from pprint import pprint

from controller.l4_loadbalancer import LoadBalancer

import time
from myutils.testhelpers import run_cmd, kill_with_children
from myutils import all_results

@defer.inlineCallbacks
def check_conns(client, server, ip, port, count=47):
    yield server.callRemote('reset_conn_count')
    yield client.callRemote('make_connections', ip, port, count=count)
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
    yield lb.commit()
    print(' --------- check that it worked ---------')
    # raw_input(' -------------------- PRESS ENTER TO CONTINUE ---------------------- ')
    yield client.callRemote('make_connections', '10.0.0.1', 8000, count=47)
    num_conns = yield server.callRemote('get_conn_count')
    print('{}/47 connections successful')
    assert num_conns == 47

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
    yield lb.commit()
    yield lb.rm_dip(pool_h, p4run.topo.get_host_ip('h3'), 8001)  # tadaaa :D
    yield lb.commit()
    print(' ----- dips: -----')
    pprint(lb.dips.data)
    print(' --------- check that it worked ---------')
    yield client.callRemote('make_connections', '10.0.0.1', 8000, count=47)
    num_conns = yield server.callRemote('get_conn_count')
    assert num_conns == 47, "everything should go to h2 because h3 was removed"
    print(' --------- try removing the last one ---------')
    yield lb.rm_dip(pool_h, p4run.topo.get_host_ip('h2'), 8001)  # remove the last one
    yield lb.commit()
    yield lb.add_dip(pool_h, p4run.topo.get_host_ip('h2'), 8001)  # re-add to check things still work
    yield lb.commit()
    yield server.callRemote('reset_conn_count')
    yield client.callRemote('make_connections', '10.0.0.1', 8000, count=47)
    num_conns = yield server.callRemote('get_conn_count')
    assert num_conns == 47, "things should still work"

@pt.inlineCallbacks
def test_commits_work(remote_module, p4run):
    lb, client, server1, server2 = yield all_results([
        LoadBalancer.get_initialised('s1', topology_db_file=p4run.topo_path),
        remote_module('myutils.client', host='h3'),
        remote_module('myutils.server', 8001, host='h1'),
        remote_module('myutils.server', 8001, host='h2'),
    ])
    server1_ip, server2_ip = [p4run.topo.get_host_ip(h) for h in ('h1', 'h2')]

    pool_handle = yield lb.add_pool('10.0.0.1', 8000)

    yield lb.add_dip(pool_handle, server1_ip, 8001)
    yield lb.commit()
    yield lb.add_dip(pool_handle, server2_ip, 8001)  # don't commit this yet
    yield check_conns(client, server1, '10.0.0.1', 8000)

    yield lb.rm_dip(pool_handle, server1_ip, 8001)
    yield lb.commit()
    yield check_conns(client, server2, '10.0.0.1', 8000)

@pt.inlineCallbacks
def test_version_rollover(remote_module, p4run):
    lb, client, server1, server2 = yield all_results([
        LoadBalancer.get_initialised('s1', topology_db_file=p4run.topo_path),
        remote_module('myutils.client', host='h3'),
        remote_module('myutils.server', 8001, host='h1'),
        remote_module('myutils.server', 8001, host='h2'),
    ])
    server1_ip, server2_ip = [p4run.topo.get_host_ip(h) for h in ('h1', 'h2')]

    pool_handle = yield lb.add_pool('10.0.0.1', 8000)

    for i in range(5):
        print(' ========== iteration {} (active version: {}) ==========='.format(
            i, lb.vips.active_version))
        yield lb.add_dip(pool_handle, server1_ip, 8001)
        yield lb.add_dip(pool_handle, server2_ip, 8001)
        yield lb.add_dip(pool_handle, server2_ip, 8002)
        yield lb.add_dip(pool_handle, server2_ip, 8003)
        yield lb.commit()
        yield lb.rm_dip(pool_handle, server2_ip, 8002)
        yield lb.rm_dip(pool_handle, server2_ip, 8003)
        yield lb.commit()
        print(' --- now I have: server{1,2}:8001: ---')
        pprint(lb.dips.data)

        yield lb.rm_dip(pool_handle, server2_ip, 8001)
        yield lb.commit()
        print(' --- now I have: server1:8001: ---')
        pprint(lb.dips.data)

        yield check_conns(client, server1, '10.0.0.1', 8000)

        yield lb.add_dip(pool_handle, server2_ip, 8001)
        yield lb.rm_dip(pool_handle, server1_ip, 8001)
        yield lb.commit()
        print(' --- now I have: server2:8001: ---')
        pprint(lb.dips.data)

        yield check_conns(client, server2, '10.0.0.1', 8000)

        yield lb.rm_dip(pool_handle, server2_ip, 8001)
        print(' --- now I have: nothing! ---')
        pprint(lb.dips.data)

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
        dhost, dport = dip
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
    yield lb.commit()

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
