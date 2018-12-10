import functools
from twisted.internet import defer
from twisted.spread import pb

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