#!/usr/bin/env python

import nnpy
from p4utils.utils.topology import Topology
from p4utils.utils.sswitch_API import SimpleSwitchAPI


class BaseController(object):
    """A base P4 switch controller that your controllers probably want to inherit from.

    Implements the digest loop. You must override the
    `recv_msg_digest(self, msg)` method if you use digest messages.

    Implements the CPU loop. You must override the
    `recv_msg_cpu(self, msg)` method if you use digest messages.

    """

    def __init__(self, sw_name, topology_db_file="./topology.db"):
        self.topo = Topology(db=topology_db_file)
        print(self.topo)
        self.sw_name = sw_name
        self.thrift_port = self.topo.get_thrift_port(sw_name)
        self.cpu_port =  self.topo.get_cpu_port_index(self.sw_name)
        self.controller = SimpleSwitchAPI(self.thrift_port)

        self.init()

    def init(self):
        self.controller.reset_state()

    def recv_msg_digest(self, msg):
        raise NotImplementedError("Digest message received, but recv_msg_digest has not been implemented")
    def recv_msg_cpu(self, msg):
        raise NotImplementedError("CPU packet received, but recv_msg_cpu has not been implemented")

    def run_digest_loop(self):
        sub = nnpy.Socket(nnpy.AF_SP, nnpy.SUB)
        notifications_socket = self.controller.client.bm_mgmt_get_info().notifications_socket
        sub.connect(notifications_socket)
        sub.setsockopt(nnpy.SUB, nnpy.SUB_SUBSCRIBE, '')

        while True:
            msg = sub.recv()
            self.recv_msg_digest(msg)




    def run_cpu_loop(self):
        cpu_port_intf = str(self.topo.get_cpu_port_intf(self.sw_name).replace("eth0", "eth1"))
        sniff(iface=cpu_port_intf, prn=self.recv_msg_cpu)

    def run_event_loop(self):
        self.run_digest_loop()
        # self.run_cpu_loop()
