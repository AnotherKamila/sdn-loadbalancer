import functools
from twisted.internet import defer, task
from twisted.protocols import basic
import os

def print_method_call(f):
    @functools.wraps(f)
    @defer.inlineCallbacks
    def wrapped(ctx, *args, **kwargs):
        name = '<'+ctx.name+'>' if hasattr(ctx, 'name') else ''
        sargs = ', '.join('{}'.format(a) for a in args)
        skws  = ', '.join({ '{}={}'.format(k,v) for k,v in kwargs.items() })
        a = ', '.join([x for x in sargs, skws if x])
        call = "{klass}{name}: {method}({args})".format(
            klass=ctx.__class__.__name__,
            name=name,
            method=f.__name__,
            args=a,
        )

        print(call)
        res = yield defer.maybeDeferred(f, ctx, *args, **kwargs)
        print("{} -> {}".format(call, res))
        defer.returnValue(res)
    return wrapped

def sleep(seconds):
    """Like time.sleep, but does not block the reactor.

    Put a yield in front."""
    from twisted.internet import reactor
    return task.deferLater(reactor, seconds, (lambda: None))


class WaitForLines(basic.LineReceiver):
    delimiter = os.linesep

    def reset(self):
        self.line_received = defer.Deferred()

    def connectionMade(self):
        self.reset()

    def lineReceived(self, line):
        callback = self.line_received.callback
        self.reset()
        callback(line)
