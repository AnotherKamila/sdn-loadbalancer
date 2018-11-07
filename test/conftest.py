import json
import os
import pytest
import re
import subprocess
import time

P4RUN_STARTUP_TIMEOUT = 30  # how long we'll wait for p4run to start up, in seconds

P4APP_EXEC_SCRIPTS_EXAMPLE = """
    "exec_scripts": [
        {
            "cmd": "touch readyfile",
            "reboot_run": "true"
        }
    ]
"""

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
            raise ValueError("{}: invalid JSON".format(p4app)) from e

    def check_touch_readyfile(exec_scripts):
        return any(script['cmd'] == 'touch readyfile' for script in exec_scripts)
    if not 'exec_scripts' in p4conf or not check_touch_readyfile(p4conf['exec_scripts']):
        raise ValueError("{} must contain an exec_scripts section such as: {}".format(p4app, P4APP_EXEC_SCRIPTS_EXAMPLE))

    ### p4run startup ###
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
    waiting = 0
    while not ready:
        time.sleep(1)
        ready = check_if_ready()
        waiting += 1
        if waiting >= P4RUN_STARTUP_TIMEOUT:
            raise Exception("p4run took too long to start")

    paranoia()
    yield p4run

    ### teardown ###
    p4run.stdin.close()  # signal p4run to exit
    p4run.wait()         # wait for clean-up
    paranoia()
