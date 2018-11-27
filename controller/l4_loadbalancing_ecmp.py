from pprint import pprint


def hostport(s):
    return s.split(':')


class ECMPMixin(object):
    """Fills the ECMP loadbalancing tables (IPv4 only):

    * ipv4_vips
    * ipv4_dips
    """
    def init_pools(self, pools):
        """pools: something like:

            POOLS = {
                '10.0.0.1:8000': ['h1:8000', 'h2:8000', 'h3:8000'],
                '10.0.0.1:9000': ['h1:9000', 'h2:9000'],
            }

        """
        # TODO UDP
        pprint(pools)
        for pool_, (vip, dips) in enumerate(pools.items()):
            pool = str(pool_)
            size = str(len(dips))
            vhost, vport = hostport(vip)
            self.controller.table_add("ipv4_vips", "set_dip_pool", [vhost, vport], [pool, size])

            for h, dip in enumerate(dips):
                dhost, dport = hostport(dip)
                dip = self.topo.get_host_ip(dhost)
                self.controller.table_add("ipv4_dips", "ipv4_tcp_rewrite_dst", [pool, str(h)], [dip, dport])

                # inverse tables:
                self.controller.table_add("ipv4_dips_inverse", "set_dip_pool_idonly", [dip, dport], [pool])
            self.controller.table_add("ipv4_vips_inverse", "ipv4_tcp_rewrite_src", [pool], [vhost, vport])
