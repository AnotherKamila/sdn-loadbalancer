#!/usr/bin/env python

from controller.base_controller_twisted import BaseController
from twisted.internet import defer

class ArpLazy(BaseController):
    """Pre-fills the ipv4_arp table based on self.topo ."""
    def init(self):
        return self.prefill_arp_table()

    @defer.inlineCallbacks
    def prefill_arp_table(self):
        # * ARP to hosts
        for h in self.topo.get_hosts_connected_to(self.sw_name):
            ip = self.topo.get_host_ip(h)
            mac = self.topo.get_host_mac(h)
            yield self.controller.table_add("ipv4_arp", "set_dst_mac", [ip], [mac])

        # * ARP to switches is not implemented because we don't need it in our project.
