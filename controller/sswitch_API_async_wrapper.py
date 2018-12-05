"""
Monkey-patches + wraps SimpleSwitchAPI to:

* defer methods to threads (so that it doesn't block the reactor) => this makes
  all methods return a Deferred

If you've loaded this module, you should not use SimpleSwitchAPI directly --
only use SimpleSwitchAPIAsyncWrapper.
"""
# This is weird. I thought it was not thread-safe, but now it seems to be
# working without the synchronisation? Well. If it starts breaking in weird
# ways, try uncommenting the stuff below :D


import functools
from p4utils.utils.runtime_API import RuntimeAPI
from p4utils.utils.sswitch_API import SimpleSwitchAPI
from twisted.internet          import threads
from twisted.python            import threadable

# Actually, the interesting methods are apparently on RuntimeAPI. Should check
# source if I want to use another method.
asyncified = [
    'table_add',
    'table_clear',
    'table_delete',
    'table_modify',
    'table_set_default',
    'table_set_timeout',
]
# synchronize all of those methods, because RuntimeAPI is *not* threadsafe
RuntimeAPI.synchronized = asyncified
threadable.synchronize(RuntimeAPI)

class SimpleSwitchAPIAsyncWrapper(object):
    """
    All non-dunder methods are deferred to a thread and return a Deferred.

    Note that the underlying thing is NOT thread-safe, so things actually
    won't happen in parallel even if you try. Everything is terrible.
    """

    def __init__(self, *args, **kwargs):
        self._switch_api = SimpleSwitchAPI(*args, **kwargs)

    def __getattr__(self, name):
        f = getattr(self._switch_api, name)
        if name not in asyncified: return f

        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            return threads.deferToThread(f, *args, **kwargs)
        return wrapped
