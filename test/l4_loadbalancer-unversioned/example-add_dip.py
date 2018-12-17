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
    print('{}/47 connections successful'.format(num_conns))
    assert num_conns == 47
