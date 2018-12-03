from twisted.internet import defer, task
from controller.base_controller_twisted import BaseController, main
from controller.l3_router_lazy          import Router
from controller.settings              import load_pools


def hostport(s):
    return s.split(':')


class LoadBalancer(Router):
    """Fills the flat loadbalancing tables (IPv4 only):

    * ipv4_vips
    * ipv4_dips

    TODO UDP :D
    """

    @defer.inlineCallbacks
    def add_pool(self, vip):
        pool_handle = str(len(self._ipv4_vips))
        vhost, vport = hostport(vip)
        self._ipv4_vips[pool_handle] = (vhost, vport)
        self._ipv4_dips[pool_handle] = []
        # on the way there table
        self._ipv4_vips_handles[pool_handle] = yield self.controller.table_add(
            "ipv4_vips", "set_dip_pool", [vhost, vport], [pool_handle, "0"])
        # inverse table
        yield self.controller.table_add(
            "ipv4_vips_inverse", "ipv4_tcp_rewrite_src", [pool_handle], [vhost, vport])
        defer.returnValue(pool_handle)

    @defer.inlineCallbacks
    def add_dip(self, pool_handle, dip):
        dhost, dport = hostport(dip)
        dip = self.topo.get_host_ip(dhost)
        flow_hash = len(self._ipv4_dips[pool_handle])
        self._ipv4_dips[pool_handle].append((dip, dport))
        yield self.controller.table_add("ipv4_dips", "ipv4_tcp_rewrite_dst", [pool_handle, str(flow_hash)], [dip, dport])
        # inverse table
        yield self.controller.table_add(
            "ipv4_dips_inverse", "set_dip_pool_idonly", [dip, dport], [pool_handle])
        yield self._fix_pool_size(pool_handle)

    @defer.inlineCallbacks
    def _fix_pool_size(self, pool_handle):
        entry_handle = self._ipv4_vips_handles[pool_handle]
        size = str(len(self._ipv4_dips[pool_handle]))
        print("modifying size for pool {} => {}".format(self._ipv4_vips[pool_handle], size))
        yield self.controller.table_modify(
            "ipv4_vips", 'set_dip_pool', entry_handle, [pool_handle, str(size)])

    def init(self):
        # TODO in an ideal world, this + handles would be abstracted
        self._ipv4_vips = {}
        self._ipv4_vips_handles = {}
        self._ipv4_dips = {}


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

# # FIXME this is not supposed to be here :D
# from twisted.spread import pb

# class LBRemoteInterface(pb.Root):
#     def remote_add_pool(self, vip):
#         return defer.succeed(47)

#     def remote_add_dip(self, pool_handle, dip):
#         return defer.succeed(42)

# # FIXME neither is this :D
# if __name__ == '__main__':
#     from twisted.internet import reactor
#     # TODO socket path should include switch name
#     reactor.listenUNIX('/tmp/p4crap-controller.socket', pb.PBServerFactory(LBRemoteInterface()))
#     reactor.run()
