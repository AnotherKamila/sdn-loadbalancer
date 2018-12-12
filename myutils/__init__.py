import functools
from twisted.spread import pb
from twisted.internet import defer


def as_list(f):
    """Decorator that changes a generator into a function that returns a list."""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        return list(f(*args, **kwargs))
    return wrapper

def print_entry_exit(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        print(' *** inside {}, args: {}, kwargs: {} *** '.format(f.__name__, args, kwargs))
        res = f(*args, **kwargs)
        print(' *** return from {}, returned: {} *** '.format(f.__name__, res))
        return res
    return wrapper

@defer.inlineCallbacks
def all_results(ds):
    results = yield defer.DeferredList(ds, fireOnOneErrback=True)
    ret = []
    for success, r in results:
        assert success
        ret.append(r)
    defer.returnValue(ret)

def deferred_print_entry_exit(f):
    @functools.wraps(f)
    @defer.inlineCallbacks
    def decorated(*args, **kwargs):
        print(' *** inside {}, args: {}, kwargs: {} *** '.format(f.__name__, args, kwargs))
        res = yield f(*args, **kwargs)
        print(' *** return from {}, returned: {} *** '.format(f.__name__, res))
        defer.returnValue(res)
    return decorated

def remote_all_the_things(cls):
    """THIS IS A TERRIBLE IDEA DO NOT USE IN PRODUCTION EVER"""
    for name, attr in cls.__dict__.items():
        if not callable(attr): continue
        setattr(cls, 'remote_'+name, attr)
    return cls


class UnexpectedServerError(pb.Error):
    pass

def raise_all_exceptions_on_client(f):
    @functools.wraps(f)
    @defer.inlineCallbacks
    def wrapped(*args, **kwargs):
        try:
            res = yield f(*args, **kwargs)
            defer.returnValue(res)
        except Exception as e:
            raise UnexpectedServerError(e)
    return wrapped
