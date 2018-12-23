import os
import time
import pytest

from myutils.testhelpers import netcat_from_to, run_cmd

from myutils.remote_utils import PYTHON_CMD_PREFIX

path    = os.path.dirname(os.path.realpath(__file__))
srv_cmd = PYTHON_CMD_PREFIX+[os.path.join(path, 'server.py')]
cli_cmd = PYTHON_CMD_PREFIX+[os.path.join(path, 'client.py')]

def hostport(s):
    return s.split(':')

def test_addr_rewriting(p4run, controller, pools):
    netcat_from_to('h4', 'h1', '10.0.1.1', port=7000)

def run_server(port, host=None, wait_to_bind=True):
    server = run_cmd(srv_cmd + [port], host, background=True)
    if wait_to_bind: time.sleep(0.5)
    return server

def get_conns_and_die(server):
    out, _ = server.communicate('die\n')
    return int(out.strip())

def run_client(nconns, shost, port, host=None):
    return run_cmd(cli_cmd + [nconns, shost, port], host)

def test_server_client():
    """Checks that the server and client are working. Does not actually use loadbalancing."""
    server = run_server(4700)
    assert run_client(10, 'localhost', 4700) == 0
    assert get_conns_and_die(server) == 10

@pytest.mark.skip(reason='flaky and weird')
def test_equal_balancing(p4run, controller, pools):
    NUM_CONNS = 1000
    TOLERANCE = 0.9
    mypool = '10.0.1.1:8000'
    pool_ip, pool_port = hostport(mypool)

    servers = []
    for s in pools[mypool]:
        host, port = hostport(s)
        servers.append(run_server(host=host, port=port, wait_to_bind=False))
    time.sleep(0.5)  # give them time to bind

    assert run_client(NUM_CONNS, pool_ip, pool_port, host='h4') == 0

    for s in servers:
        assert get_conns_and_die(s) >= TOLERANCE*NUM_CONNS/len(pools[mypool])
