import functools
import itertools
import time
from twisted.internet import defer
from twisted.spread import pb

from myutils.testhelpers import run_cmd, kill_with_children
from myutils.twisted_utils import sleep

_processes = []
def process(cmd, host=None, background=True):
    _processes.append((run_cmd(cmd, host, background=True), host))

def kill_all_my_children():
    for p, host in _processes:
        # cannot exit them with .terminate() if they're in mx :-(
        assert kill_with_children(p) == 0


def sock(*args):
    return '/tmp/p4crap-{}.socket'.format('-'.join(str(a) for a in args))

def python_m(module, *args):
    time.sleep(0.1) # pipenv run opens Pipfile in exclusive mode or something,
                    # and then it throws up when I run more of them
                    # using time.sleep because I *want* to block the reactor
    return ['pipenv', 'run', 'python', '-m', module] + list(args)

_sock_counter = itertools.count(1)
@defer.inlineCallbacks
def remote_module(mname, *m_args, **p_kwargs):
    """Run a PB-using module in a separate process and give back its root object.

    param mname: module name
    param *m_args: CLI args, will be added after `python -m mname`
    param *p_kwargs: will be passed to the process executor
    """
    sock_name = sock(mname, next(_sock_counter))
    process(python_m(mname, sock_name, *m_args), **p_kwargs)
    yield sleep(2)  # wait for it to bind
    conn = pb.PBClientFactory()
    from twisted.internet import reactor
    reactor.connectUNIX(sock_name, conn)
    obj = yield conn.getRootObject()
    defer.returnValue(obj)
