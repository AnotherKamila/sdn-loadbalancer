import json
import os
import pytest
import re
import subprocess
import time

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
        self.topo = Topology(db=os.path.join(workdir, "topology.db"))

    def host_IPs(self):
        """Returns a dict of hosts and IPs.

        Returns the first IP of a host if there are multiple.
        """
        return { h: self.topo.get_host_ip(h) for h in self.topo.get_hosts() }

    def iponly(self, ip):
        """Utility function to strip netmask from IP: iponly('10.0.0.1/24') => '10.0.0.1'"""
        return ip.split('/')[0]


@pytest.fixture(scope='module')
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
            p4conf = json.loads(p4json.read())
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


@pytest.fixture(scope='module')
def controller(request):
    """Runs our controller for each switch in the topology.

    "Our controller" means something called "controller.py" in the test directory;
    you might want to symlink something from /controller, such as:
    cd basic; ln -s ../../controller/l2_controller.py ./controller.py
    """
    testdir = request.fspath.dirname  # work in the test directory
    exe     = os.path.join(testdir, './controller.py')
    
    if not os.path.exists(exe):
        raise ValueError('controller.py not exist in {}'.format(testdir))

    p4 = P4Obj(testdir)

    def start_ctrls():
        for s in p4.topo.get_p4switches():
            yield subprocess.Popen(
                ['python', './controller.py', s],
                cwd=testdir,
            )
    ctrls = list(start_ctrls())
    time.sleep(3)  # wait for the controller to fill out the initial tables
    for c in ctrls:
        retcode = c.poll()
        if retcode != None:
            raise Exception("controller.py exited with error status: {}".format(retcode))
    return ctrls
