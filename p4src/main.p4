/* -*- P4_16 -*- */
#include <core.p4>
#include <v1model.p4>

#include "settings.p4"   // table sizes, register widths, and such
#include "headers.p4"    // packet headers, plus the metadata struct
#include "parsers.p4"    // parser and deparser
#include "checksums.p4"  // checksum verification and computation

/*************************************************************************
***************  I N G R E S S   P R O C E S S I N G   *******************
*************************************************************************/

control MyIngress(inout headers hdr,
                  inout metadata meta,
                  inout standard_metadata_t standard_metadata) {

    action drop() {
        mark_to_drop();
    }

    /************************* L3 / ROUTING ******************************/

    action ipv4_through_gateway(ipv4_addr_t gateway, interface_t iface) {
        meta.out_interface = iface;
        meta.ipv4_next_hop = gateway;  // send through the gateway
    }

    action ipv4_direct(interface_t iface) {
        meta.out_interface = iface;
        meta.ipv4_next_hop = hdr.ipv4.dst_addr;  // send directly to the destination
    }

    table ipv4_routing {
        key = {
            hdr.ipv4.dst_addr: lpm;  // match prefixes
        }
        actions = {
            ipv4_through_gateway;    // ipv4_through_gateway(gateway, iface)
            ipv4_direct;             // ipv4_direct(iface)
            drop;
        }
        // If there is no route, drop it -- in reality, we might want to
        // send an ICMP "No route to host" packet.
        // Note that this is the default route, so control plane might
        // want to set a default gateway here instead of dropping.
        default_action = drop();
        size = ROUTING_TABLE_SIZE;
    }
    
    /************************* L2.5 / ARP+NDP GLUE ************************/

    action set_dst_mac(mac_addr_t dst_addr) {
        hdr.ethernet.dst_addr = dst_addr;
    }

    table ipv4_arp {
        key = {
            meta.ipv4_next_hop: exact;  // next_hop is the host we found in the routing step
            // meta.out_interface: exact;  // actually next_hop is unique, so leaving this out
        }
        actions = {
            set_dst_mac;                    // set_dst_mac(mac)
            drop;
        }
        default_action = drop();
        size = ARP_TABLE_SIZE;
    }

    /************************* L2 / SWITCHING ****************************/

    action forward(bit<9> port) {
        standard_metadata.egress_spec = port;
    }

    action set_mcast_grp(bit<16> group){
	standard_metadata.mcast_grp = group;
    }

    action mac_learn(){
	meta.learn.mac_src_addr = hdr.ethernet.src_addr;
	meta.learn.ingress_port = (bit<16>) standard_metadata.ingress_port;
    }

    table smac {
         key = {hdr.ethernet.src_addr: exact;}

         actions = {
		mac_learn;
		NoAction;
         }
         default_action = mac_learn;
         size = ARP_TABLE_SIZE;
    }

    table dmac {
        key = {hdr.ethernet.dst_addr: exact;}

        actions = {
                forward;
		NoAction;
        }
        default_action = NoAction;
        size = ARP_TABLE_SIZE;
    }

    table broadcast {
        key = {standard_metadata.ingress_port: exact;}

        actions = {
		set_mcast_grp;
		NoAction;
        }
        default_action = NoAction;
        size = ARP_TABLE_SIZE;
    }

    apply {
        ipv4_routing.apply();
        ipv4_arp.apply();
        smac.apply();
        if (!dmac.apply().hit){
            // Real switches drop when no match -- this opens up a DOS attack.
            // We don't care, so we just broadcast.
            broadcast.apply();
        }
    }
}

/*************************************************************************
*****************  E G R E S S   P R O C E S S I N G   *******************
*************************************************************************/

control MyEgress(inout headers hdr,
                 inout metadata meta,
                 inout standard_metadata_t standard_metadata) {
    apply {}
}

/*************************************************************************
****************************  S W I T C H  *******************************
*************************************************************************/

V1Switch(
    MyParser(),
    MyVerifyChecksum(),
    MyIngress(),
    MyEgress(),
    MyComputeChecksum(),
    MyDeparser()
) main;
