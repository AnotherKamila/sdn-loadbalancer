#!/usr/bin/env python

import struct

from controller.base_controller import BaseController

class L2SwitchLazy(BaseController):
    """Pre-fills the MAC table based on self.topo ."""

    # TODO add an on_init decorator :D
    def init(self):
        super(L2SwitchLazy, self).init()
        self.prefill_mac_table()

    def prefill_mac_table(self):
        # * MAC associations to hosts
        for h in self.topo.get_hosts_connected_to(self.sw_name):
            mac  = self.topo.get_host_mac(h)
            port = self.topo.node_to_node_port_num(self.sw_name, h)
            self.controller.table_add("mac", "forward", [mac], [str(port)])

        # * MAC associations to other switches not implemented because I don't need it in this project.


if __name__ == "__main__":
    import sys
    sw_name = sys.argv[1]
    controller = L2SwitchLazy(sw_name).run_event_loop()
