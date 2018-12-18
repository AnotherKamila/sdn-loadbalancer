from __future__ import print_function

from twisted.internet                   import defer, task
from controller.base_controller_twisted import BaseController, main
from controller.l3_router_lazy          import Router
from controller.settings                import load_pools, p4settings
from controller.p4table                 import P4Table, VersionedP4Table
from myutils.twisted_utils              import print_method_call
from myutils import all_results
from pprint import pprint
import scapy.all as scapy

BLOOM_FILTER_ENTRIES = p4settings['BLOOM_FILTER_ENTRIES']
MAX_TABLE_VERSIONS   = p4settings['MAX_TABLE_VERSIONS']

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

        self.pool_IPs    = {}  # pool => (vip, vport)
        self.pool_hashes = {}  # pool => { (dip, dport) => [hash] }

    @print_method_call
    @defer.inlineCallbacks
    def add_pool(self, vip, vport):
        pool = len(self.vips)
        yield self.vips.add([vip, vport], 'set_dip_pool', [pool, 0])
        yield self.vips_inverse.add([pool], 'ipv4_tcp_rewrite_src', [vip, vport])
        self.pool_IPs[pool] = (vip, vport)
        self.pool_hashes[pool] = {}
        defer.returnValue(pool)

    @print_method_call
    @defer.inlineCallbacks
    def add_dip(self, pool, dip, dport):
        self.pool_hashes[pool][(dip, dport)] = []
        yield self.dips_inverse.add([dip, dport], 'set_dip_pool_idonly', [pool])
        yield self.set_dip_weight(pool, dip, dport, 1)  # default to 1

    def get_dip_weight(self, pool, dip, dport):
        return len(self.pool_hashes[pool][(dip, dport)])

    @print_method_call
    @defer.inlineCallbacks
    def set_dip_weight(self, pool, dip, dport, weight):
        diff = weight - self.get_dip_weight(pool, dip, dport)
        # do we want to add or remove?
        fn = self._inc_dip_weight if diff > 0 else self._dec_dip_weight
        for i in range(abs(diff)): yield fn(pool, dip, dport)
        yield self._set_pool_size(pool)

    def get_pool_size(self, pool):
        return sum(len(hashlist) for hashlist in self.pool_hashes[pool].values())

    @print_method_call
    @defer.inlineCallbacks
    def _inc_dip_weight(self, pool, dip, dport):
        next_hash = self.get_pool_size(pool)
        yield self.dips.add([pool, next_hash], 'ipv4_tcp_rewrite_dst', [dip, dport])
        self.pool_hashes[pool][(dip, dport)].append(next_hash)

    @print_method_call
    @defer.inlineCallbacks
    def _dec_dip_weight(self, pool, dip, dport):
        # In order to not mess up hashes, I need to swap this with the last one
        # instead of just deleting it.
        size      = self.get_pool_size(pool)
        last_hash = size - 1
        my_hash   = self.pool_hashes[pool][(dip, dport)].pop()
        if my_hash != last_hash:
            # Exchange last_hash and my_hash:
            # last_hash needs to go away, my_hash will be reused for that other dip
            last_dip, last_dport  = self.dips[(pool, last_hash)][1]
            self.pool_hashes[pool][(last_dip, last_dport)].remove(last_hash)
            self.pool_hashes[pool][(last_dip, last_dport)].append(my_hash)
            yield self.dips.modify([pool, my_hash], 'ipv4_tcp_rewrite_dst', [last_dip, last_dport])
        yield self.dips.rm([pool, last_hash])

    @print_method_call
    @defer.inlineCallbacks
    def rm_dip(self, pool, dip, dport):
        yield self.set_dip_weight(pool, dip, dport, 0)  # remove all of them
        yield self.dips_inverse.rm([dip, dport])

    @print_method_call
    @defer.inlineCallbacks
    def _set_pool_size(self, pool, size=None):
        if not size: size = self.get_pool_size(pool)
        print("modifying size for pool {} ({}) => {}".format(self.pool_IPs[pool], pool, size))
        yield self.vips.modify(self.pool_IPs[pool], 'set_dip_pool', [pool, size])


class LoadBalancerAtomic(LoadBalancerUnversioned):
    @defer.inlineCallbacks
    def init(self):
        self.vips = yield VersionedP4Table.get_initialised(
            self.controller,
            'ipv4_vips',
            version_signalling_register=('table_versions', 0),
            max_versions=MAX_TABLE_VERSIONS,
        )
        self.vips_inverse = yield VersionedP4Table.get_initialised(
            self.controller,
            'ipv4_vips_inverse',
            version_signalling_register=None,
            max_versions=MAX_TABLE_VERSIONS,
        )
        self.dips = yield VersionedP4Table.get_initialised(
            self.controller,
            'ipv4_dips',
            version_signalling_register=None,
            max_versions=MAX_TABLE_VERSIONS,
        )
        self.dips_inverse = yield VersionedP4Table.get_initialised(
            self.controller,
            'ipv4_dips_inverse',
            version_signalling_register=None,
            max_versions=MAX_TABLE_VERSIONS,
        )

    @print_method_call
    @defer.inlineCallbacks
    def commit(self):
        # First clear out the Bloom filter for the version that is about to become active.
        yield self.controller.register_reset('bloom_filter_{}'.format(self.vips.next_version))

        # Doesn't look like it, but the signalling is in fact atomic, because
        # the P4 code uses the vips signal for all tables.
        # We call the other 3 just to tell Python that we have advanced the versions.
        yield self.vips.commit_and_slide()
        yield self.vips_inverse.commit_and_slide()
        yield self.dips.commit_and_slide()
        yield self.dips_inverse.commit_and_slide()


class CPU(scapy.Packet):
    name = 'CpuPacket'
    fields_desc = [
        scapy.BitField('ipv4_pools_version', 3, p4settings['TABLE_VERSIONS_SIZE']),
        scapy.BitField('flow_hash',          3, 6),
    ]

class LoadBalancer(LoadBalancerAtomic):
    def init(self):
        # TODO things from the conn_table need to expire

        # 5-tuple => ipv4_tcp_rewrite_{dst,src} addr port
        self.conn_table = P4Table(self.controller, 'ipv4_tcp_conn_table')
        self.pending_conn_writes = [[] for i in range(self.vips.max_versions)]
        self.start_sniffer_thread()

    def parse_packet(self, packet):
        cpu = CPU(str(packet.payload))
        ip  = scapy.IP(str(cpu.payload))
        tcp = scapy.TCP(str(ip.payload))
        return cpu, (ip.src, tcp.sport, ip.dst, tcp.dport, ip.proto)

    def recv_packet(self, packet):
        meta, fivetuple = self.parse_packet(packet)
        src, sport, dst, dport, proto = fivetuple
        version, hash = meta.ipv4_pools_version, meta.flow_hash
        _, (pool, size)   = self.vips.versioned_data[version][(dst, dport)]
        _, (dip, dipport) = self.dips.versioned_data[version][(pool, hash)]

        if (src, sport, dst, dport, proto) in self.conn_table.data: return  # done already

        self.pending_conn_writes[version].append(
            self.conn_table.add(
                [src, sport, dst, dport, proto],
                'ipv4_tcp_rewrite_dst',
                [dip, dipport]
            )
        )
        self.pending_conn_writes[version].append(
            self.conn_table.add(
                [dip, dipport, src, sport, proto],
                'ipv4_tcp_rewrite_src',
                [dst, dport]
            )
        )

    @defer.inlineCallbacks
    def commit(self):
        # Commit will overwrite next_version, so I wait for all conn_table
        # writes of next_version to complete before rolling over.
        yield defer.DeferredList(
            self.pending_conn_writes[self.vips.next_version],
            fireOnOneErrback=True
        )
        self.pending_conn_writes[self.vips.next_version] = []
        yield LoadBalancerAtomic.commit(self)


BUCKETS_PER_POOL = 64

class MetricsLoadBalancer(LoadBalancer):
    """Periodically queries the servers for load and adjusts weights accordingly.

    @param get_metrics: function: (dip, port) -> something

    @param metrics_to_weights: function [something] -> [int]
           Determines the behavior: what weights do we assign given these loads?

           This is the application-specific behavior that you'll want to change.
           Pass the metrics_to_weights parameter to init to override this.
    """
    def __init__(self, sw_name, get_metrics, metrics_to_weights=None, *args, **kwargs):
        LoadBalancer.__init__(self, sw_name, *args, **kwargs)
        self.get_metrics = get_metrics
        self.metrics_to_weights = metrics_to_weights or self.default_metrics_to_weights
        self.adjust_weights_loop = task.LoopingCall(self.adjust_weights)

    def default_metrics_to_weights(self, loads):
        relative_weights = [1.0/load for load in loads]
        return [
            int(BUCKETS_PER_POOL * weight / sum(relative_weights))
            for weight in relative_weights
        ]

    @print_method_call
    @defer.inlineCallbacks
    def adjust_weights(self):
        for pool, dips in self.pool_hashes.items():
            # print('++++++++ {} +++++++++'.format(dips.keys()))
            loads = yield all_results([
                defer.maybeDeferred(self.get_metrics, *dip)
                for dip in dips.keys()
            ])
            wanted_weights = self.metrics_to_weights(loads)
            for (dip, dport), wanted_weight in zip(dips.keys(), wanted_weights):
                yield self.set_dip_weight(pool, dip, dport, wanted_weight)
        yield self.commit()

    def start_loop(self, seconds=5):
        self.adjust_weights_loop.start(seconds)

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
