import json
import os
import re
import subprocess
import time
import pytest
import pytest_twisted as pt
from twisted.spread import pb
from twisted.internet import defer, task, reactor
import itertools

from controller.l4_loadbalancer import LoadBalancer

from myutils.testhelpers import run_cmd, kill_with_children
from myutils import all_results
from myutils.twisted_utils import sleep
from myutils.remote_utils import python_m

from p4utils.utils.topology import Topology

P4RUN_STARTUP_TIMEOUT = 30  # how long we'll wait for p4run to start up, in seconds

P4APP_EXEC_SCRIPTS_EXAMPLE = """
    "exec_scripts": [
        {
            "cmd": "touch readyfile",
            "reboot_run": "true"
        }
    ]
"""

class P4Obj:
    """Utility class for p4run-related stuff. Given by the p4run fixture."""
    def __init__(self, workdir):
        self.topo_path = os.path.join(workdir, "topology.db")
        self.topo = Topology(self.topo_path)

    def host_IPs(self):
        """Returns a dict of hosts and IPs.

        Returns the first IP of a host if there are multiple.
        """
        return { h: self.topo.get_host_ip(h) for h in self.topo.get_hosts() }

    def iponly(self, ip):
        """Utility function to strip netmask from IP: iponly('10.0.0.1/24') => '10.0.0.1'"""
        return ip.split('/')[0]


@pytest.fixture(scope='function')
def p4run(request):
    """A fixture to automatically launch `p4run` when running tests.

    It uses the `p4app.json` present in the directory where the test file
    lives.

    Your `p4app.json` MUST contain this:

    ```
    "exec_scripts": [
        {
            "cmd": "touch readyfile",
            "reboot_run": "true"
        }
    ]
    ```
    Otherwise this code won't be able to find out that p4run is ready and will
    timeout.

    The value of the fixture is a P4Obj (defined here).
    """
    testdir = request.fspath.dirname  # work in the test directory
    p4app     = os.path.join(testdir, 'p4app.json')
    readyfile = os.path.join(testdir, 'readyfile')

    ### provide some user-friendly error messages instead of weird failures ###
    # I am secretly a nice person!
    if not os.path.exists(p4app):
        raise ValueError('p4app.json does not exist in {}'.format(testdir))

    p4conf = None
    with open(p4app) as p4json:
        try:
            p4conf = json.load(p4json)
        except json.decoder.JSONDecodeError as e:
            raise ValueError("{}: invalid JSON".format(p4app))

    def check_touch_readyfile(exec_scripts):
        return any(script['cmd'] == 'touch readyfile' for script in exec_scripts)
    if not 'exec_scripts' in p4conf or not check_touch_readyfile(p4conf['exec_scripts']):
        raise ValueError("{} must contain an exec_scripts section such as: {}".format(p4app, P4APP_EXEC_SCRIPTS_EXAMPLE))

    ### p4run startup ###
    def paranoia():  # keep running this all the time, just in case :D
        subprocess.call(['rm', '-f', readyfile])

    paranoia()
    p4run = subprocess.Popen(
        ['sudo', 'p4run', '--quiet'],
        cwd=testdir,            # in this test's directory
        stdin=subprocess.PIPE,  # we want to use this to control mininet CLI
    )
    # We need to wait for it to be ready! This is a pain in the butt :'(
    # How I do it: I put `touch readyfile` into p4app.json; the scripts get run when ready, so it works.
    def check_if_ready():
        return os.path.exists(readyfile)

    ready = False
    waiting = 0
    while not ready:
        time.sleep(1)
        ready = check_if_ready()
        waiting += 1
        if waiting >= P4RUN_STARTUP_TIMEOUT:
            raise Exception("p4run took too long to start")

    paranoia()
    yield P4Obj(testdir)

    ### teardown ###
    p4run.stdin.close()  # signal p4run to exit
    p4run.wait()         # wait for clean-up
    paranoia()


@pytest.fixture(scope='function')
def controller(request):
    """Runs our controller for each switch in the topology.

    "Our controller" means an executable called "./controller" in the test directory;
    you might want it to call something from controller/, such as:

        #!/bin/sh
        python -m controller.l3_controller $1

    """
    testdir = request.fspath.dirname  # work in the test directory
    exe     = os.path.join(testdir, './controller')

    if not os.path.exists(exe):
        raise ValueError('./controller does not exist in {}'.format(testdir))
    if not os.access(exe, os.X_OK):
        raise ValueError('./controller is not executable: in {}'.format(testdir))

    p4 = P4Obj(testdir)

    def start_ctrls():
        for s in p4.topo.get_p4switches():
            yield subprocess.Popen(
                ['./controller', s],
                cwd=testdir,
            )
    ctrls = list(start_ctrls())
    time.sleep(3)  # wait for the controller to fill out the initial tables
    for c in ctrls:
        retcode = c.poll()
        if retcode not in [None, 0]:
            raise Exception("controller exited with error status: {}".format(retcode))
    return ctrls


################### Twisted helpers ###################

@pytest.fixture()
def process(request):
    ps = []
    def run(cmd, host=None, background=True):
        ps.append((run_cmd(cmd, host, background=True), host))
    yield run
    for p, host in ps:
        # cannot exit them with .terminate() if they're in mx :-(
        # p.terminate()
        assert kill_with_children(p) == 0

def sock(*args):
    return '/tmp/p4crap-{}.socket'.format('-'.join(str(a) for a in args))

@pytest.fixture()
def remote_module(request, process):
    sock_counter = itertools.count(1)
    remotes = []

    @defer.inlineCallbacks
    def run(module, *m_args, **p_kwargs):
        sock_name = sock(module, next(sock_counter))
        process(python_m(module, sock_name, *m_args), **p_kwargs)
        yield sleep(2)
        conn = pb.PBClientFactory()
        reactor.connectUNIX(sock_name, conn)
        obj = yield conn.getRootObject()
        remotes.append(obj)
        defer.returnValue(obj)

    return run
