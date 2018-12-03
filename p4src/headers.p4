/* -*- P4_16 -*- */
/* packet headers, plus the metadata struct */
#ifndef HEADERS_P4
#define HEADERS_P4


#include <core.p4>
#include <v1model.p4>

typedef bit<48>  mac_addr_t;
typedef bit<9>   port_t;
typedef bit<32>  ipv4_addr_t;
typedef bit<128> ipv6_addr_t;
typedef bit<16>  l4_port_t;   // tcp or udp port

// the following types are used only internally
// => sizes can be changed
typedef bit<4> interface_t;
typedef bit<6> dip_pool_t;
typedef bit<6> pool_size_t;

const bit<16> TYPE_IPV4 = 0x0800;
const bit<16> TYPE_IPV6 = 0x86DD;
const bit<8>  TYPE_TCP  = 6;


header ethernet_t {
    mac_addr_t dst_addr;
    mac_addr_t src_addr;
    bit<16>    ethertype;
}

header ipv4_t {
    bit<4>      version;
    bit<4>      ihl;
    bit<8>      diffserv;
    bit<16>     total_len;
    bit<16>     identification;
    bit<3>      flags;
    bit<13>     frag_offset;
    bit<8>      ttl;
    bit<8>      protocol;
    bit<16>     hdr_checksum;
    ipv4_addr_t src_addr;
    ipv4_addr_t dst_addr;
}

/* https://en.wikipedia.org/wiki/IPv6_packet */
header ipv6_t {
    bit<4>      version;
    bit<8>      traffic_class;
    bit<20>     flow_label;
    bit<16>     payload_length;
    bit<8>      next_header;
    bit<8>      hop_limit;
    ipv6_addr_t src_addr;
    ipv6_addr_t dst_addr;
}

header tcp_t{
    l4_port_t src_port;
    l4_port_t dst_port;
    bit<32>   seq_no;
    bit<32>   ack_no;
    bit<4>    data_offset;
    bit<3>    res;
    bit<9>    flags;
    bit<16>   window;
    bit<16>   checksum;
    bit<16>   urgent_ptr;
}

struct headers {
    ethernet_t ethernet;
    ipv4_t     ipv4;
    ipv6_t     ipv6;
    tcp_t	     tcp;
}

struct metadata {
    bit<16> l4_payload_length;

    interface_t out_interface; // in SDN, an interface is a software-only concept (TODO really?)

    ipv4_addr_t ipv4_next_hop; // at most one will be present,
    ipv6_addr_t ipv6_next_hop; // depending on what we're sending out

    dip_pool_t  dip_pool;      // Direct IP pool -- pool of servers we are loadbalancing to
    pool_size_t pool_size;     // Note: This field could be removed by restructuring the code, if short on memory
    pool_size_t flow_hash;     // [0, pool size)
}


#endif
