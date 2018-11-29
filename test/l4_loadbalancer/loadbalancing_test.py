import os
import time

from myutils.testhelpers import netcat_from_to, run_cmd, run_on_host

path    = os.path.dirname(os.path.realpath(__file__))
srv_cmd = ['pipenv', 'run', os.path.join(path, 'server.py')]
cli_cmd = ['pipenv', 'run', os.path.join(path, 'client.py')]

def hostport(s):
    return s.split(':')

def test_addr_rewriting(p4run, controller, pools):
    netcat_from_to('h4', 'h1', '10.0.1.1', port=7000)

def test_server_client():
    """Checks that the server and client are working. Does not actually use loadbalancing."""
    server = run_cmd(srv_cmd + [4700], background=True)
    time.sleep(1)

    assert run_cmd(cli_cmd + [10, 'localhost', 4700]) == 0
    out, _ = server.communicate('end\n')  # request that it dies
    n_conns = int(out.strip())
    assert n_conns == 10

# TODO needs faster switch => turn off debugging
def test_equal_balancing(p4run, controller, pools):
    NUM_CONNS = 1000
    TOLERANCE = 0.9
    mypool = '10.0.1.1:8000'
    pool_ip, pool_port = hostport(mypool)

    servers = []
    for s in pools[mypool]:
        host, port = hostport(s)
        servers.append(run_on_host(host, srv_cmd + [port], background=True))
    time.sleep(1)

    assert run_on_host('h4', cli_cmd + [NUM_CONNS, pool_ip, pool_port]) == 0

    for s in servers:
        out, _ = s.communicate('end\n')  # request that they die
        n_conns = int(out.strip())
        assert n_conns >= TOLERANCE*NUM_CONNS/len(pools[mypool])
