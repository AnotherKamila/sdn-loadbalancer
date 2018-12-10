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

    // Use this when that thing should never happen.
    action panic() {
        // should send what went wrong, but that sounds like work :D
        drop();
    }

    /************************* TABLE VERSIONING *************************/

    register<table_version_t>(1) table_versions;  // will be written to by the control plane
    action init_versioning() {
        table_versions.read(meta.ipv4_pools_version, 0);
    }

    /*********************** L4 / LOAD BALANCING *************************/
    // IMPORTANT: I am only handling IPv4 and TCP here!

    action ipv4_tcp_learn_connection() {
        // TODO
    }
    action ipv4_tcp_rewrite_dst(ipv4_addr_t daddr, l3_port_t dport) {
        hdr.ipv4.dst_addr = daddr;
        hdr.tcp.dst_port  = dport;
    }
    action ipv4_tcp_rewrite_src(ipv4_addr_t saddr, l3_port_t sport) {
        hdr.ipv4.src_addr = saddr;
        hdr.tcp.src_port  = sport;
    }

    table ipv4_tcp_conn_table {
        key = {
            hdr.ipv4.src_addr: exact;
            hdr.tcp.src_port:  exact;
            hdr.ipv4.dst_addr: exact;
            hdr.tcp.dst_port:  exact;
            hdr.ipv4.protocol: exact;
        }
        actions = {
            ipv4_tcp_rewrite_dst;      // on the way there
            ipv4_tcp_rewrite_src;      // on the way back
            NoAction;
        }
        default_action = NoAction;
        size = CONN_TABLE_SIZE;
    }

    // check bloom filters: is this a new-ish conn with a version?
    action ipv4_tcp_check_new_conn_pool_version() {
        // TODO check Bloom filters
        // note that init_versioning has set the current as default
    }

    // 1. should we loadbalance? where to?

    action set_dip_pool(dip_pool_t pool, pool_size_t size) {
        meta.dip_pool  = pool;
        meta.pool_size = size;
    }

    // Virtual IPs -- the IPs we are load balancing
    // this is a table because we want to be able to change it at runtime;
    // and then we can easily have multiple pools for loadbalancing more
    // applications, so why not :D
    table ipv4_vips {
        key = {
            meta.ipv4_pools_version: exact;
            hdr.ipv4.dst_addr: exact;
            hdr.tcp.dst_port:  exact;
        }
        actions = {
            set_dip_pool;
            NoAction;
        }
        default_action = NoAction();
        size = VIP_TABLE_SIZE;
    }

    // 2. compute flow hash
    // Must be applied in the main apply loop, otherwise it would be ugly with v4/v6 stuff
    // TODO note that this only processes TCP, UDP would need its own function
    // or copying to meta
    action ipv4_compute_flow_hash() {
        hash(
            meta.flow_hash,
            HashAlgorithm.crc32,
            (bit<1>)0,
            { hdr.ipv4.src_addr,
              hdr.ipv4.dst_addr,
              hdr.tcp.src_port,
              hdr.tcp.dst_port,
              hdr.ipv4.protocol },
            meta.pool_size
        );
    }

    // 3. stick flow into a server
    table ipv4_dips {
        key = {
            meta.ipv4_pools_version: exact;
            meta.dip_pool:  exact;
            meta.flow_hash: exact;
        }
        actions = {
            ipv4_tcp_rewrite_dst;
            NoAction;
        }
        default_action = NoAction();
        size = DIP_TABLE_SIZE;
    }

    ///////////////// ON THE WAY BACK: We need to undo the NATting //////////

    // Note: This is ahem a bit awkward! This should be per connection --
    // because what if someone connects to the same thing directly. FIXME!!!
    // TODO I should either track whether the connection is NATted
    // (so a set membership/bloom filter) OR drop direct connections to backends.
    // Ask the TA!

    // We could do this in one table, but that would require a lot more space,
    // so instead I'll "normalise the tables" and split it into two, joinable
    // by the pool ID.
    action set_dip_pool_idonly(dip_pool_t pool) {
        meta.dip_pool  = pool;
    }
    table ipv4_dips_inverse {
        key = {
            meta.ipv4_pools_version: exact;
            hdr.ipv4.src_addr: exact;
            hdr.tcp.src_port:  exact;
        }
        actions = {
            set_dip_pool_idonly;
            NoAction;
        }
        default_action = NoAction();
        size = DIP_TABLE_SIZE;
    }

    // IMPORTANT: This table must only be applied if the previous one matched!
    // We really don't want src rewriting on the way in :D
    table ipv4_vips_inverse {
        key = {
            meta.ipv4_pools_version: exact;
            meta.dip_pool: exact;
        }
        actions = {
            ipv4_tcp_rewrite_src;
            NoAction;
        }
        default_action = NoAction();
        size = DIP_TABLE_SIZE;
    }

    /************************* L3 / ROUTING ******************************/

    ///////// v6

    action ipv6_decrease_hop_limit() {
        hdr.ipv6.hop_limit = hdr.ipv6.hop_limit - 1;
    }

    action ipv6_through_gateway(ipv6_addr_t gateway, interface_t iface) {
        meta.out_interface = iface;
        meta.ipv6_next_hop = gateway;  // send through the gateway
    }

    action ipv6_direct(interface_t iface) {
        meta.out_interface = iface;
        meta.ipv6_next_hop = hdr.ipv6.dst_addr;  // send directly to the destination
    }

    table ipv6_routing {
        key = {
            hdr.ipv6.dst_addr: lpm;  // match prefixes
        }
        actions = {
            ipv6_through_gateway;    // ipv6_through_gateway(gateway, iface)
            ipv6_direct;             // ipv6_direct(iface)
            drop;
        }
        // If there is no route, drop it -- in reality, we might want to
        // send an ICMP "No route to host" packet.
        // Note that this is the default route, so control plane might
        // want to set a default gateway here instead of dropping.
        default_action = drop();
        size = ROUTING_TABLE_SIZE;
    }

    ///////// v4

    action ipv4_decrease_ttl() {
        hdr.ipv4.ttl = hdr.ipv4.ttl - 1;
    }
    
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
    // for simplicity, tables filled out in the controller

    action set_dst_mac(mac_addr_t dst_addr) {
        hdr.ethernet.dst_addr = dst_addr;
    }

    table ipv6_ndp {
        key = {
            meta.ipv6_next_hop: exact;  // next_hop is the host we found in the routing step
            // meta.out_interface: exact;  // actually next_hop is unique, so leaving this out
        }
        actions = {
            set_dst_mac;                    // set_dst_mac(mac)
            drop;
        }
        default_action = drop();
        size = ARP_TABLE_SIZE;
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

    table mac {
        key = {hdr.ethernet.dst_addr: exact;}

        actions = {
            forward;
            drop;
        }
        default_action = drop;
        size = ARP_TABLE_SIZE;
    }

    // Note: All of this uses tables pre-filled by the controller.
    // There is no MAC or ARP.
    // Wheee.
    apply {
        init_versioning();

        //////// L4/TCP LOADBALANCING ////////
        if (hdr.tcp.isValid() && hdr.ipv4.isValid()) {
            ipv4_tcp_conn_table.apply(); // 0. is this a known connection?

            // 1. check bloom filters: is this a new-ish conn with a version?
            ipv4_tcp_check_new_conn_pool_version(); // fills out meta.ipv4_pool_version

            // 2. rewrite its dst
            if (ipv4_vips.apply().hit) {
                ipv4_tcp_learn_connection(); // hit on vips => this needs translation & wasn't in conn_table
                ipv4_compute_flow_hash();
                ipv4_dips.apply();
            } else {
                if (ipv4_dips_inverse.apply().hit) {
                    ipv4_vips_inverse.apply();
                }
            }
        }
        /// Note: no loadbalancing for UDP! //
        /////////////// L3/IPv6 ////////////// 
        if (hdr.ipv6.isValid()) {
            // ipv6_decrease_hop_limit();
            // if (hdr.ipv6.hop_limit == 0) drop();
            ipv6_routing.apply();
            ipv6_ndp.apply();
        }

        /////////////// L3/IPv4 ////////////// 
        if (hdr.ipv4.isValid()) {
            // IPv4 routing
            ipv4_routing.apply();
            ipv4_decrease_ttl();
            if (hdr.ipv4.ttl == 0) drop();
            ipv4_arp.apply();
        }

        //////////////// L2 //////////////// 
        mac.apply();
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
