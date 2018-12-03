#!/usr/bin/env python

from controller.base_controller_twisted import BaseController, main
from controller.l2_lazy           import L2SwitchLazy
from controller.arp_lazy          import ArpLazy
from controller.ipv4_routing_topo import IPv4Routing

class Router(IPv4Routing, ArpLazy, L2SwitchLazy, BaseController):
    pass  # :D


if __name__ == "__main__":
   main(Router)
