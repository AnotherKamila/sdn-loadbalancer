#!/usr/bin/env python

import nnpy
import struct
from controller.l2_learning import L2Switch

# In theory, this should be using IPv4RoutingMixin, but it doesn't because this is all a hack and that would be complicated.

# TODO remove once p4utils supports v6
# careful with this: *must* match the actual topology from p4app.json hack
IPV6_OVERRIDES = {
    'h1': 'fd00::1',
    'h2': 'fd00::2',
    'h3': 'fd00::3',
}
IPV6_DIRECT_NETWORKS = [
    'fd00::/64',
]

class Controller(L2Switch):
    def init(self):
        super(Controller, self).init()
        self.init_lazy_tables()
        self.init_routing()

    def init_routing(self):
        """Initialises the routing tables:

        * ipv4_routing
        * ipv6_routing
        """
        # * IPv4 direct
        for iface, net in enumerate(self.topo.get_direct_host_networks_from_switch(self.sw_name)):
            self.controller.table_add('ipv4_routing', 'ipv4_direct', [net], [str(iface)])

        # * IPv6 direct
        for iface, net in enumerate(IPV6_DIRECT_NETWORKS):
            self.controller.table_add('ipv6_routing', 'ipv6_direct', [net], [str(iface)])

        # * Gateways are not here, because we don't need them in our project.
        #   In reality, they would be added either statically or via a
        #   control-plane routing protocol such as BGP.

    def init_lazy_tables(self):
        """
        Initialises the content of tables that we aren't learning:

        * ipv4_arp
        * ipv6_ndp
        """
        # * ARP + NDP to hosts
        for h in self.topo.get_hosts_connected_to(self.sw_name):
            table = None
            if h in IPV6_OVERRIDES:
                table = "ipv6_ndp"
                ip = IPV6_OVERRIDES[h]
            else:
                table = "ipv4_arp"
                ip = self.topo.get_host_ip(h)
            mac = self.topo.get_host_mac(h)
            self.controller.table_add(table, "set_dst_mac", [ip], [mac])

        # * ARP+NDP to switches is not implemented because we don't need it in our project.


if __name__ == "__main__":
    import sys
    sw_name = sys.argv[1]
    controller = Controller(sw_name).run_digest_loop()

