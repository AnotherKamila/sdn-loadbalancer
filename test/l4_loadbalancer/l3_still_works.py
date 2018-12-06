from __future__ import print_function

import pytest_twisted as pt
import pytest
from twisted.internet import defer, reactor
from pprint import pprint

from controller.l4_loadbalancer import LoadBalancer

import time
from myutils.testhelpers import run_cmd, kill_with_children
from myutils import all_results

@pt.inlineCallbacks
def test_direct_conn(remote_module, p4run):
    print(' --------- prepare server, client, and loadbalancer ---------')
    client, server, lb = yield all_results([
        remote_module('myutils.client', host='h1'),
        remote_module('myutils.server', 8000, host='h2'),
        LoadBalancer.get_initialised('s1', topology_db_file=p4run.topo_path),
    ])
    print(" --------- add a random pool: unused, just to make sure it doesn't mess things up ---------")
    pool_h = yield lb.add_pool('10.0.0.1', 4700)
    yield lb.add_dip(pool_h, p4run.topo.get_host_ip('h1'), 4700)
    yield lb.add_dip(pool_h, p4run.topo.get_host_ip('h2'), 4700)
    yield lb.commit()
    print(' --------- check that it worked ---------')
    yield client.callRemote('make_connections', p4run.topo.get_host_ip('h2'), 8000, count=47)
    num_conns = yield server.callRemote('get_conn_count')
    assert num_conns == 47
