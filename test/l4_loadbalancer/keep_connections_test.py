from __future__ import print_function, unicode_literals

import pytest_twisted as pt
import pytest
import time
from twisted.internet import defer, reactor
from twisted.spread import pb
from pprint import pprint
from myutils import all_results

from controller.l4_loadbalancer import LoadBalancer


@pt.inlineCallbacks
def test_echo_client(remote_module):
    client, server = yield all_results([
        remote_module('myutils.client', host=None),
        remote_module('myutils.server', 8000, host=None),
    ])
    yield client.callRemote('start_echo_clients', 'localhost', 8000, count=5)
    time.sleep(0.5)  # make sure the clients have connected
    yield client.callRemote('close_all_connections')

    nconns1 = yield server.callRemote('get_conn_count')
    assert nconns1 == 5

    # TODO!
    # with pytest.raises(pb.RemoteError) as excinfo:
    #     yield client.callRemote('start_echo_clients', 'localhost', 8900, count=5)
    #     time.sleep(0.5)  # make sure the clients have connected
    #     nconns1 = yield server.callRemote('get_conn_count')
    # assert 'ConnectionFailed' in str(excinfo)


@pt.inlineCallbacks
def test_old_versions(remote_module, p4run):
    lb, client, server1 = yield all_results([
        LoadBalancer.get_initialised('s1', topology_db_file=p4run.topo_path),
        remote_module('myutils.client', host='h3'),
        remote_module('myutils.server', 8001, host='h1'),
    ])
    server1_ip, server2_ip = [p4run.topo.get_host_ip(h) for h in ('h1', 'h2')]

    pool_handle = yield lb.add_pool('10.0.0.1', 8000)
    print(' --------- v1: {server1} ---------')
    yield lb.add_dip(pool_handle, server1_ip, 8001)
    yield lb.commit()
    yield client.callRemote('start_echo_clients', '10.0.0.1', 8000, count=5)
    time.sleep(0.5)  # make sure the clients have connected
    print(' --------- v2: {server2} ---------')
    yield lb.rm_dip(pool_handle, server1_ip, 8001)
    yield lb.add_dip(pool_handle, server2_ip, 8001)
    yield lb.commit()
    time.sleep(0.5)  # give it time to notice the breakage, if any

    # test #1: this does not explode :D -- this would throw if something bad happened to the connections
    yield client.callRemote('close_all_connections')

    nconns = yield server1.callRemote('get_conn_count')
    assert nconns == 5


