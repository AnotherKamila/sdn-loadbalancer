#!/usr/bin/env python

import struct

from controller.base_controller_twisted import BaseController, main
from twisted.internet import defer
from myutils import all_results

class L2SwitchLazy(BaseController):
    """Pre-fills the MAC table based on self.topo ."""

    def init(self):
        return self.prefill_mac_table()

    @defer.inlineCallbacks
    def prefill_mac_table(self):
        # * MAC associations to hosts
        ds = []
        for h in self.topo.get_hosts_connected_to(self.sw_name):
            mac  = self.topo.get_host_mac(h)
            port = self.topo.node_to_node_port_num(self.sw_name, h)
            ds.append(self.controller.table_add("mac", "forward", [mac], [str(port)]))
        yield all_results(ds)

        # * MAC associations to other switches not implemented because I don't need it in this project.


if __name__ == "__main__":
    main(L2SwitchLazy)
