import pytest_twisted as pt
import pytest
import os
from twisted.internet import defer

from controller.l4_loadbalancer import LoadBalancer

# FIXME rewrite these to do the right thing
import time
from myutils.testhelpers import run_cmd

# FIXME ======================== hi :D =======================================
path    = os.path.dirname(os.path.realpath(__file__))
srv_cmd = ['pipenv', 'run', os.path.join(path, 'server.py')]
cli_cmd = ['pipenv', 'run', os.path.join(path, 'client.py')]

def hostport(s):
    return s.split(':')

def run_server(port, host=None, wait_to_bind=True):
    server = run_cmd(srv_cmd + [port], host, background=True)
    if wait_to_bind: time.sleep(0.5)
    return server

def get_conns_and_die(server):
    out, _ = server.communicate('die\n')
    return int(out.strip())

def run_client(nconns, shost, port, host=None):
    return run_cmd(cli_cmd + [nconns, shost, port], host)
# FIXME ================ the brokenness hopefully ends here ==================

path = os.path.dirname(os.path.realpath(__file__))

def run_python_m(module, args=[], host=None, background=True):
    return run_cmd(['pipenv', 'run', 'python', '-m', module]+args, host, background)

@pt.inlineCallbacks
def test_equal_balancing_inprocess(p4run):
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

####################################################################

@pytest.fixture()
def process(request):
    ps = []
    def run(cmd, host=None, background=True):
        ps.append(run_cmd(cmd, host, background=True))
    yield run

    for p in ps:
        p.terminate()

def python_m(module, args=None):
    if not args: args = []
    return ['pipenv', 'run', 'python', '-m', module]+args

@pt.inlineCallbacks
def test_inprocess_server_client(process):
    process(python_m('myutils.server'))
    process(python_m('myutils.client'))
    time.sleep(1.5)  # wait for bind

    from twisted.spread import pb
    from twisted.internet import reactor

    server_conn = pb.PBClientFactory()
    client_conn = pb.PBClientFactory()
    print('***** here 1 ******')
    reactor.connectUNIX('/tmp/p4crap-server.socket', server_conn)
    reactor.connectUNIX('/tmp/p4crap-client.socket', client_conn)
    print('***** here 2 ******')
    server = yield server_conn.getRootObject()
    client = yield client_conn.getRootObject()
    print('***** here 3 ******')
    yield client.callRemote('make_connections', 'localhost', 8000, count=47)
    num_conns = yield server.callRemote('get_conn_count')
    print('***** here 4 ******')
    assert num_conns == 47
