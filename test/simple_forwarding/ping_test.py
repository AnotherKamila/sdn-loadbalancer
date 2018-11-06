import pytest
import os
import time
import subprocess

# TODO this could be discovered by topology
hosts = {
    "h1": "10.0.0.1",
    "h2": "10.0.0.2",
    "h3": "10.0.0.3",
    "h4": "10.0.0.4",
}

def ping_from_to(h1, h2):
    cmd = ['mx', h1, 'ping', '-c1', hosts[h2]]
    return subprocess.run(cmd)

def test_ping_works(p4run):
    for h1 in sorted(hosts.keys()):
        for h2 in sorted(hosts.keys()):
            ping = ping_from_to(h1, h2)
            assert ping.returncode == 0

# TODO this should not be needed in every file
@pytest.fixture
def p4run():
    # TODO clean up this horrible mess
    testdir = os.path.dirname(__file__)
    readyfile = os.path.join(testdir, 'readyfile')
    def paranoia():  # keep running this all the time, just in case :D
        subprocess.run(['rm', '-f', readyfile])

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
    while not ready:
        time.sleep(1)
        ready = check_if_ready()

    paranoia()
    return p4run

    # teardown
    p4run.stdin.close()  # signal p4run to exit
    p4run.wait()         # wait for clean-up
    paranoia()
