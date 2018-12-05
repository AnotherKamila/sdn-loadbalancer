import attr
from twisted.internet import defer, task
from controller.base_controller_twisted import BaseController, main
from controller.l3_router_lazy          import Router
from controller.settings              import load_pools


def hostport(s):
    return s.split(':')


import functools

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


@attr.s
class P4Table(object):
    name       = attr.ib()
    controller = attr.ib()
    data    = attr.ib(factory=dict)

    def __getitem__(self, key):
        # TODO
        # assert isinstance(key, iterable)
        return self.data[key]

    def __setitem__(self, key, value):
        raise NotImplementedError("To write to the table, use the .add / .modify methods.")

    def __len__(self):
        return len(self.data)

    @print_method_call
    @defer.inlineCallbacks
    def add(self, keys, action, values):
        keys, values = self._fix_keys_values(keys, values)
        assert keys not in self.data, "add called with duplicate keys!"
        res = yield self.controller.table_add(self.name, action, keys, values)
        assert res != None, "table_add failed!"
        self.data[keys]    = (action, values)

    @print_method_call
    @defer.inlineCallbacks
    def modify(self, keys, new_action, new_values):
        keys, new_values = self._fix_keys_values(keys, new_values)
        assert keys in self.data, "modify called without existing entry!"
        res = yield self.controller.table_modify_match(self.name, new_action, keys, new_values)
        print(' ----- table_modify returned: {} -----'.format(res))
        self.data[keys] = (new_action, new_values)

    def _fix_keys_values(self, keys, values):
        keys   = tuple(str(k) for k in keys)
        values = tuple(str(v) for v in values)
        return keys, values

class LoadBalancer(Router):
    """Fills the flat loadbalancing tables (IPv4 only):

    * ipv4_vips + inverse
    * ipv4_dips + inverse

    TODO IPv6
    TODO UDP
    """

    def init(self):
        # ipv4.dst_addr tcp.dst_port => set_dip_pool pool size
        self.vips = P4Table('ipv4_vips', self.controller)
        # pool flow_hash => ipv4_tcp_rewrite_dst daddr dport
        self.dips = P4Table('ipv4_dips', self.controller)
        # saddr sport => set_dip_pool_idonly pool
        self.dips_inverse = P4Table('ipv4_dips_inverse', self.controller)
        # pool => ipv4_tcp_rewrite_src saddr sport
        self.vips_inverse = P4Table('ipv4_vips_inverse', self.controller)

        self.pool_IPs      = {}
        self.pool_contents = {}

    @print_method_call
    @defer.inlineCallbacks
    def add_pool(self, vip):
        # TODO the API should be (host, port) tuple instead of joint address thing
        pool = len(self.vips)
        vhost, vport = hostport(vip)
        yield self.vips.add([vhost, vport], 'set_dip_pool', [pool, 0])
        yield self.vips_inverse.add([pool], 'ipv4_tcp_rewrite_src', [vhost, vport])
        self.pool_IPs[pool] = (vhost, vport)
        self.pool_contents[pool] = set()
        defer.returnValue(pool)

    @print_method_call
    @defer.inlineCallbacks
    def add_dip(self, pool, dip):
        # TODO maybe the API shouldn't use pool handles, just (host, port) tuples
        dhost, dport = hostport(dip)
        # FIXME the person who wrote this code was an idiot -- this should get IP, not hostname!!!
        dip = self.topo.get_host_ip(dhost)
        next_hash = len(self.pool_contents[pool])
        yield self.dips.add([pool, next_hash], 'ipv4_tcp_rewrite_dst', [dip, dport])
        yield self.dips_inverse.add([dip, dport], 'set_dip_pool_idonly', [pool])
        self.pool_contents[pool].add((dhost, dport))
        yield self._fix_pool_size(pool)

    # @defer.inlineCallbacks
    def set_weight(self, dip, weight):
        pass  # TODO

    @print_method_call
    @defer.inlineCallbacks
    def _fix_pool_size(self, pool):
        size = len(self.pool_contents[pool])
        print("modifying size for pool {} ({}) => {}".format(self.pool_IPs[pool], pool, size))
        yield self.vips.modify(self.pool_IPs[pool], 'set_dip_pool', [pool, size])


@defer.inlineCallbacks
def init_pools_json(lb):
    pools = load_pools('./pools.json')
    for vip, dips in pools.items():
        handle = yield lb.add_pool(vip)
        for dip in dips:
            yield lb.add_dip(handle, dip)

@defer.inlineCallbacks
def main(reactor, sw_name):
    lb = yield LoadBalancer.get_initialised(sw_name)
    yield init_pools_json(lb)

if __name__ == '__main__':
    import sys
    sw_name = sys.argv[1] if len(sys.argv) > 1 else 's1'
    task.react(main, [sw_name])
