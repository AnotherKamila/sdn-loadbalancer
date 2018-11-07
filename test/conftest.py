import subprocess
import pytest
import os
import time

@pytest.fixture(scope='module')
def p4run(request):
    # TODO clean up this horrible mess
    # from ptpython.repl import embed
    # embed(globals(), locals())  # has access to all the variables

    testdir = request.fspath.dirname  # work in the test directory
    readyfile = os.path.join(testdir, 'readyfile')
    print(readyfile)
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
