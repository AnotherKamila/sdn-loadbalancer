#!/usr/bin/env python

class ArpLazyMixin(object):
    """Pre-fills the ipv4_arp table based on self.topo ."""
    def init(self):
        super(ArpLazyMixin, self).init()
        self.prefill_arp_table()

    def prefill_arp_table(self):
        # * ARP to hosts
        for h in self.topo.get_hosts_connected_to(self.sw_name):
            ip = self.topo.get_host_ip(h)
            mac = self.topo.get_host_mac(h)
            self.controller.table_add("ipv4_arp", "set_dst_mac", [ip], [mac])

        # * ARP to switches is not implemented because we don't need it in our project.
