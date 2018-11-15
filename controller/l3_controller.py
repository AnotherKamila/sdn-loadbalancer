import nnpy
import struct
from p4utils.utils.topology import Topology
from p4utils.utils.sswitch_API import SimpleSwitchAPI
from scapy.all import Ether, sniff, Packet, BitField

class Controller(object):

    def __init__(self, sw_name):

        self.topo = Topology(db="./topology.db")
        print(self.topo)
        self.sw_name = sw_name
        self.thrift_port = self.topo.get_thrift_port(sw_name)
        self.cpu_port =  self.topo.get_cpu_port_index(self.sw_name)
        self.controller = SimpleSwitchAPI(self.thrift_port)

        self.init()

    def init(self):

        self.controller.reset_state()
        self.add_broadcast_groups()
        self.add_mirror()
        self.init_lazy_tables()
        self.init_routing()

    def add_mirror(self):
        if self.cpu_port:
            self.controller.mirroring_add(100, self.cpu_port)

    def add_broadcast_groups(self):
        interfaces_to_port = self.topo[self.sw_name]["interfaces_to_port"].copy()
        #filter lo and cpu port
        interfaces_to_port.pop('lo', None)
        interfaces_to_port.pop(self.topo.get_cpu_port_intf(self.sw_name), None)

        mc_grp_id = 1
        rid = 0
        for ingress_port in interfaces_to_port.values():

            port_list = interfaces_to_port.values()[:]
            del(port_list[port_list.index(ingress_port)])

            #add multicast group
            self.controller.mc_mgrp_create(mc_grp_id)

            #add multicast node group
            handle = self.controller.mc_node_create(rid, port_list)

            #associate with mc grp
            self.controller.mc_node_associate(mc_grp_id, handle)

            #fill broadcast table
            self.controller.table_add("broadcast", "set_mcast_grp", [str(ingress_port)], [str(mc_grp_id)])

            mc_grp_id +=1
            rid +=1


    def init_routing(self):
        """Initialises the routing tables:

        * ipv4_routing
        * ipv6_routing [LATER]
        """
        for iface, net in enumerate(self.topo.get_direct_host_networks_from_switch(self.sw_name)):
            self.controller.table_add('ipv4_routing', 'ipv4_direct', [net], [str(iface)])
        # TODO gateways :D

    def init_lazy_tables(self):
        """
        Initialises the content of tables that we aren't learning:

        * ipv4_arp
        * ipv6_ndp [LATER]
        """
        for h in self.topo.get_hosts_connected_to(self.sw_name):
            iface = '0'  # TODO determine iface somehow
            ip    = self.topo.get_host_ip(h)
            mac   = self.topo.get_host_mac(h)
            self.controller.table_add("ipv4_arp", "set_dst_mac", [ip, iface], [mac])

    def learn(self, learning_data):
        for mac_addr, ingress_port in  learning_data:
            print "mac: %012X ingress_port: %s " % (mac_addr, ingress_port)
            self.controller.table_add("smac", "NoAction", [str(mac_addr)])
            self.controller.table_add("dmac", "forward", [str(mac_addr)], [str(ingress_port)])

    def unpack_digest(self, msg, num_samples):
        digest = []
        print len(msg), num_samples
        starting_index = 32
        for sample in range(num_samples):
            mac0, mac1, ingress_port = struct.unpack(">LHH", msg[starting_index:starting_index+8])
            starting_index +=8
            mac_addr = (mac0 << 16) + mac1
            digest.append((mac_addr, ingress_port))

        return digest

    def recv_msg_digest(self, msg):
        topic, device_id, ctx_id, list_id, buffer_id, num = struct.unpack("<iQiiQi",
                                                                          msg[:32])
        digest = self.unpack_digest(msg, num)
        self.learn(digest)

        #Acknowledge digest
        self.controller.client.bm_learning_ack_buffer(ctx_id, list_id, buffer_id)


    def run_digest_loop(self):
        sub = nnpy.Socket(nnpy.AF_SP, nnpy.SUB)
        notifications_socket = self.controller.client.bm_mgmt_get_info().notifications_socket
        sub.connect(notifications_socket)
        sub.setsockopt(nnpy.SUB, nnpy.SUB_SUBSCRIBE, '')

        while True:
            msg = sub.recv()
            self.recv_msg_digest(msg)

if __name__ == "__main__":
    import sys
    sw_name = sys.argv[1]
    controller = Controller(sw_name).run_digest_loop()

