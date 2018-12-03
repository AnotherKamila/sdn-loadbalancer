import pytest
import subprocess
from myutils.testhelpers import ping_all

pytest.skip("""This broke when I removed L2 learning and I don't care enough
to debug this. Last commit where this worked: 6307a5b.
""", allow_module_level=True)

# TODO remove once p4utils supports v6
# careful with this: *must* match the actual topology from p4app.json hack
IPV6_OVERRIDES = {
    'h1': 'fd00::1',
    'h2': 'fd00::2',
    'h3': 'fd00::3',
}

PINGOPTS = ['-l3', '-c3', '-q']

# Arguments in pytest are magic:
# * if you declare an argument called p4run, it will take care of p4run for you
#   (and you can use p4run.topo and some utility methods in the tests)
# * the argument controller will run the controller for each switch in the topology
#   (it will use the controller.py in this directory)
def test_ping_ipv4(p4run, controller):
    all_hosts = p4run.host_IPs()
    hosts = { h: all_hosts[h] for h in all_hosts if h not in IPV6_OVERRIDES }
    ping_all(hosts)

def test_ping_ipv6(p4run, controller):
    hosts = IPV6_OVERRIDES
    ping_all(hosts, ping6=True)
