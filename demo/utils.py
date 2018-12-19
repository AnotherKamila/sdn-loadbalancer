from datetime import datetime
from twisted.internet import defer, task
from myutils import all_results

POOL_HANDLE = 0  # assume we want graphs for pool 0

def setup_graph(server_IPs, lb, loadavg=10):
    servers = [s for ip,s in sorted(server_IPs.items())]

    with open('./data.tsv', 'w') as f: pass  # the easiest way to truncate it :D
    demo_start = datetime.now()

    @defer.inlineCallbacks
    def update_graph():
        weights = [lb.get_dip_weight(POOL_HANDLE, ip,p) for (ip,p) in sorted(server_IPs.keys())]
        loads   = yield all_results([server.callRemote('get_load', loadavg) for server in servers])
        conns   = yield all_results([server.callRemote('get_conn_count')    for server in servers])
        now     = (datetime.now() - demo_start).total_seconds()

        data = [now]+weights+loads+conns
        with open('./data.tsv', 'a') as f:
            f.write('{}\n'.format('\t'.join([str(x) for x in data])))
            f.flush()

    graph_loop = task.LoopingCall(update_graph)
    graph_loop.start(0.5)
