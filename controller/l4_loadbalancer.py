from twisted.internet                   import defer, task
from controller.base_controller_twisted import BaseController, main
from controller.l3_router_lazy          import Router
from controller.settings                import load_pools
from controller.p4table                 import P4Table, VersionedP4Table
from myutils.twisted_utils              import print_method_call
from pprint import pprint


class LoadBalancerUnversioned(Router):
    """Fills the flat loadbalancing tables (IPv4 only):

    * ipv4_vips + inverse
    * ipv4_dips + inverse

    TODO IPv6
    TODO UDP
    """

    def init(self):
        # ipv4.dst_addr tcp.dst_port => set_dip_pool pool size
        self.vips         = P4Table(self.controller, 'ipv4_vips')
        # pool flow_hash => ipv4_tcp_rewrite_dst daddr dport
        self.dips         = P4Table(self.controller, 'ipv4_dips')
        # saddr sport => set_dip_pool_idonly pool
        self.dips_inverse = P4Table(self.controller, 'ipv4_dips_inverse')
        # pool => ipv4_tcp_rewrite_src saddr sport
        self.vips_inverse = P4Table(self.controller, 'ipv4_vips_inverse')

        self.pool_IPs      = {}  # pool => (vip, vport)
        self.pool_contents = {}  # pool => { (dip, dport) => hash }

    @print_method_call
    @defer.inlineCallbacks
    def add_pool(self, vip, vport):
        pool = len(self.vips)
        yield self.vips.add([vip, vport], 'set_dip_pool', [pool, 0])
        yield self.vips_inverse.add([pool], 'ipv4_tcp_rewrite_src', [vip, vport])
        self.pool_IPs[pool] = (vip, vport)
        self.pool_contents[pool] = {}
        defer.returnValue(pool)

    @print_method_call
    @defer.inlineCallbacks
    def add_dip(self, pool, dip, dport):
        # TODO maybe the API shouldn't use pool handles, just (host, port) tuples
        next_hash = len(self.pool_contents[pool])
        yield self.dips.add([pool, next_hash], 'ipv4_tcp_rewrite_dst', [dip, dport])
        yield self.dips_inverse.add([dip, dport], 'set_dip_pool_idonly', [pool])
        self.pool_contents[pool][(dip, dport)] = next_hash
        yield self._set_pool_size(pool)

    @print_method_call
    @defer.inlineCallbacks
    def rm_dip(self, pool, dip, dport):
        # TODO I could probably save myself some awfulness by wanting a handle instead of dip and dport.
        if (dip, dport) not in self.pool_contents[pool]:
            raise ValueError("{}:{}: no such DIP in pool {}:{}".format(dip, dport, *self.pool_IPs[pool]))
        # In order to not mess up hashes, I need to swap this with the last one
        # instead of just deleting it.
        size      = len(self.pool_contents[pool])
        my_hash   = self.pool_contents[pool][(dip, dport)]
        last_hash = size - 1
        last_dip, last_dport  = self.dips[(pool, last_hash)][1]
        last_dport = int(last_dport)  # GRAAAAAAAAAAAH
        # First decrease size => don't leave the tables in a weird state
        self._set_pool_size(pool, size - 1)
        if my_hash != last_hash:
            yield self.dips.modify([pool, my_hash], 'ipv4_tcp_rewrite_dst', [last_dip, last_dport])
            self.pool_contents[pool][(last_dip, last_dport)] = my_hash
        yield self.dips.rm([pool, last_hash])
        yield self.dips_inverse.rm([dip, dport])
        del self.pool_contents[pool][(dip, dport)]

    # @defer.inlineCallbacks
    def set_weight(self, dip, dport, weight):
        pass  # TODO

    @print_method_call
    @defer.inlineCallbacks
    def _set_pool_size(self, pool, size=None):
        if not size: size = len(self.pool_contents[pool])
        print("modifying size for pool {} ({}) => {}".format(self.pool_IPs[pool], pool, size))
        yield self.vips.modify(self.pool_IPs[pool], 'set_dip_pool', [pool, size])


class LoadBalancer(LoadBalancerUnversioned):
    def init(self):
        self.vips = VersionedP4Table(self.controller, 'ipv4_vips',
            version_signalling_register=('table_versions', 0),
            max_versions=4,
        )
        self.vips_inverse = VersionedP4Table(self.controller, 'ipv4_vips_inverse',
            version_signalling_register=None,
            max_versions=4,
        )
        self.dips = VersionedP4Table(self.controller, 'ipv4_dips',
            version_signalling_register=None,
            max_versions=4,
        )
        self.dips_inverse = VersionedP4Table(self.controller, 'ipv4_dips_inverse',
            version_signalling_register=None,
            max_versions=4,
        )

    @print_method_call
    @defer.inlineCallbacks
    def commit(self):
        # Doesn't look like it, but the signalling is in fact atomic, because
        # the P4 code uses the vips signal for all tables.
        # We call the other 3 just to tell Python that we have advanced the versions.
        yield self.vips.commit_and_slide()
        yield self.vips_inverse.commit_and_slide()
        yield self.dips.commit_and_slide()
        yield self.dips_inverse.commit_and_slide()


##### The rest of this file is here for compatibility with old tests only. #####

@defer.inlineCallbacks
def init_pools_json(lb):
    def hostport(s):
        r = s.split(':')
        return r[0], int(r[1])

    pools = load_pools('./pools.json')
    for vip, dips in pools.items():
        handle = yield lb.add_pool(*hostport(vip))
        for dip in dips:
            h, p = hostport(dip)
            yield lb.add_dip(handle, lb.topo.get_host_ip(h), p)

@defer.inlineCallbacks
def main(reactor, sw_name):
    """Only used in old-style tests. Don't use it in new ones."""
    lb = yield LoadBalancerUnversioned.get_initialised(sw_name)
    yield init_pools_json(lb)

if __name__ == '__main__':
    import sys
    sw_name = sys.argv[1] if len(sys.argv) > 1 else 's1'
    task.react(main, [sw_name])
