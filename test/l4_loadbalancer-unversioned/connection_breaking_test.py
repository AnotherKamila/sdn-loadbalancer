from __future__ import print_function, unicode_literals

import pytest
import pytest_twisted as pt
from twisted.spread import pb
from myutils import all_results
from myutils.twisted_utils import sleep

from controller.l4_loadbalancer import LoadBalancer, LoadBalancerUnversioned

@pt.inlineCallbacks
def test_connections_break(remote_module, p4run):
    """
    Tests that connections break when the pool changes. Exists to avoid false positives.

    Same as `l4_loadbalancer/keep_connections_test.py:test_old_versions`,
    but uses the unversioned thing and expects it to fail."""
    lb, client, server1, server2 = yield all_results([
        LoadBalancerUnversioned.get_initialised('s1', topology_db_file=p4run.topo_path),
        remote_module('myutils.client', host='h3'),
        remote_module('myutils.server', 8001, host='h1'),
        remote_module('myutils.server', 8001, host='h2'),
    ])
    yield sleep(0.5)
    server1_ip, server2_ip = [p4run.topo.get_host_ip(h) for h in ('h1', 'h2')]

    pool_handle = yield lb.add_pool('10.0.0.1', 8000)
    print(' --------- create a pool with server1 ---------')
    yield lb.add_dip(pool_handle, server1_ip, 8001)
    yield client.callRemote('start_echo_clients', '10.0.0.1', 8000, count=5)
    yield sleep(0.5)  # make sure the clients have connected
    print(' --------- break it: change the pool ---------')
    yield lb.rm_dip(pool_handle, server1_ip, 8001)
    yield lb.add_dip(pool_handle, server2_ip, 8001)
    yield sleep(0.5)  # give time to notice the breakage

    with pytest.raises(pb.RemoteError) as excinfo:
        # this should throw a ConnectionLost, because we broke the connections
        yield client.callRemote('close_all_connections')
    assert 'ConnectionLost' in str(excinfo)
