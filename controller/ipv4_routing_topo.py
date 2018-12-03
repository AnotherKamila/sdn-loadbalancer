#!/usr/bin/env python

from twisted.internet import defer
from controller.base_controller_twisted import BaseController

class IPv4Routing(BaseController):
    """Initialises the ipv4_routing table from self.topo ."""
    def init(self):
        return self.init_routing()

    @defer.inlineCallbacks
    def init_routing(self):
        # * IPv4 direct
        for iface, net in enumerate(self.topo.get_direct_host_networks_from_switch(self.sw_name)):
            yield self.controller.table_add('ipv4_routing', 'ipv4_direct', [net], [str(iface)])

        # * Gateways are not here, because we don't need them in our project.
        #   In reality, they would be added either statically or via a
        #   control-plane routing protocol such as BGP.

