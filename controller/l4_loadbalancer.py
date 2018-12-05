from twisted.internet                   import defer, task
from controller.base_controller_twisted import BaseController, main
from controller.l3_router_lazy          import Router
from controller.settings                import load_pools
from controller.p4table                 import P4Table
from myutils.twisted_utils              import print_method_call


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
    def add_pool(self, vip, vport):
        pool = len(self.vips)
        yield self.vips.add([vip, vport], 'set_dip_pool', [pool, 0])
        yield self.vips_inverse.add([pool], 'ipv4_tcp_rewrite_src', [vip, vport])
        self.pool_IPs[pool] = (vip, vport)
        self.pool_contents[pool] = set()
        defer.returnValue(pool)

    @print_method_call
    @defer.inlineCallbacks
    def add_dip(self, pool, dip, dport):
        # TODO maybe the API shouldn't use pool handles, just (host, port) tuples
        next_hash = len(self.pool_contents[pool])
        yield self.dips.add([pool, next_hash], 'ipv4_tcp_rewrite_dst', [dip, dport])
        yield self.dips_inverse.add([dip, dport], 'set_dip_pool_idonly', [pool])
        self.pool_contents[pool].add((dip, dport))
        yield self._fix_pool_size(pool)

    # def rm_dip(self, pool, dip, dport):


    # @defer.inlineCallbacks
    def set_weight(self, dip, dport, weight):
        pass  # TODO

    @print_method_call
    @defer.inlineCallbacks
    def _fix_pool_size(self, pool):
        size = len(self.pool_contents[pool])
        print("modifying size for pool {} ({}) => {}".format(self.pool_IPs[pool], pool, size))
        yield self.vips.modify(self.pool_IPs[pool], 'set_dip_pool', [pool, size])


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
    lb = yield LoadBalancer.get_initialised(sw_name)
    yield init_pools_json(lb)

if __name__ == '__main__':
    import sys
    sw_name = sys.argv[1] if len(sys.argv) > 1 else 's1'
    task.react(main, [sw_name])
