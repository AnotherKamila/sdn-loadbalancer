import functools


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

def deferred_print_entry_exit(f):
    @functools.wraps(f)
    @defer.inlineCallbacks
    def decorated(*args, **kwargs):
        print(' *** inside {}, args: {}, kwargs: {} *** '.format(f.__name__, args, kwargs))
        res = yield f(*args, **kwargs)
        print(' *** return from {}, returned: {} *** '.format(f.__name__, res))
        defer.returnValue(res)
    return decorated
