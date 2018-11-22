import functools
import re

from fabric import ThreadingGroup


UPTIME_PATTERN = r'load average\w*: ([0-9.]+)'

def as_list(f):
    """Decorator that changes a generator into a function that returns a list."""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        return list(f(*args, **kwargs))
    return wrapper


class Hosts:
    """Returns the loads of a group of hosts. Reuses the connections."""
    def __init__(self, hosts, **kwargs):
        """Accepts a list of hostnames, + kwargs which will be passed to Fabric."""
        self.conns = ThreadingGroup(*hosts, **kwargs)

    @as_list
    def get_loads(self):
        """Returns the loads as a list of floats in the order in which the hosts were given."""
        for conn in self.conns:
            uptime = conn.run('uptime', hide=True)
            yield float(re.search(UPTIME_PATTERN, uptime.stdout).group(1))
