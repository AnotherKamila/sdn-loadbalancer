import pytest_twisted as pt
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

def run_python_m(module, host, background=True):
    return run_cmd(['pipenv', 'run', 'python', '-m', module], host, background)

@pt.inlineCallbacks
def test_equal_balancing_inprocess(p4run):
    NUM_CONNS = 1000
    TOLERANCE = 0.9

    mypool = '10.0.1.1:8000'
    myservers = ['h1:8001', 'h2:8002', 'h3:8003']

    servers = []
    for s in myservers:
        host, port = hostport(s)
        servers.append(run_server(host=host, port=port, wait_to_bind=False))
    time.sleep(0.5)  # give them time to bind

    lb = yield LoadBalancer.get_initialised('s1')

    handle = yield lb.add_pool(mypool)
    for dip in myservers:
        yield lb.add_dip(handle, dip)

    pool_ip, pool_port = hostport(mypool)
    assert run_client(NUM_CONNS, pool_ip, pool_port, host='h4') == 0

    for s in servers:
        assert get_conns_and_die(s) >= TOLERANCE*NUM_CONNS/len(myservers)


    # # ctrl = yield LoadBalancer.get_initialised('s1')
    # ctrl_process = run_python_m('controller.l4_loadbalancer_flat', host='h1')
    # time.sleep(0.5)


    # from twisted.spread import pb
    # from twisted.internet import reactor

    # ctrl_client_factory = pb.PBClientFactory()
    # reactor.connectUNIX('/tmp/p4crap-controller.socket', ctrl_client_factory)
    # ctrl = yield ctrl_client_factory.getRootObject()

    # pool1 = yield ctrl.callRemote("add_pool", mypool)
    # # FIXME
    # assert pool1 == 47

    # setups = []
    # servers = []
    # for s in ["h1:8001", "h2:8002", "h3:8003"]:
    #     setups.append(ctrl.callRemote("add_dip", pool1, s))
    #     h, p = hostport(s)
    #     servers.append(run_server(p, host=h))  # TODO setups.append and things

    # # FIXME
    # results = yield defer.DeferredList(setups)  # wait for setup things to complete
    # assert len(results) == 3
    # for r in results:
    #     assert r == (True, 42)

    # # TODO :D
    # # assert run_client(NUM_CONNS, pool_ip, pool_port, host='h4') == 0

    # # TODO :D
    # # for s in servers:
    # #     assert get_conns_and_die(s) >= TOLERANCE*NUM_CONNS/len(pools[mypool])
