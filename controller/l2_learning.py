#!/usr/bin/env python

import struct

from controller.base_controller import BaseController

class L2Switch(BaseController):

    def init(self):
        super(L2Switch, self).init()
        self.add_broadcast_groups()

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

    def recv_msg_cpu(self, pkt):

        packet = Ether(str(pkt))

        if packet.type == 0x1234:
            cpu_header = CpuHeader(packet.payload)
            self.learn([(cpu_header.macAddr, cpu_header.ingress_port)])



if __name__ == "__main__":
    import sys
    sw_name = sys.argv[1]
    controller = L2Switch(sw_name).run_event_loop()
