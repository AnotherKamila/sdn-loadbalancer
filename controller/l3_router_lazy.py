#!/usr/bin/env python

from controller.l2_learning       import L2Switch
from controller.arp_lazy          import ArpLazyMixin
from controller.ipv4_routing_topo import IPv4RoutingMixin


class Router(IPv4RoutingMixin, ArpLazyMixin, L2Switch):
    pass  # :D


if __name__ == "__main__":
    import sys
    sw_name = sys.argv[1]
    controller = Router(sw_name).run_digest_loop()
