import functools


def as_list(f):
    """Decorator that changes a generator into a function that returns a list."""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        return list(f(*args, **kwargs))
    return wrapper
