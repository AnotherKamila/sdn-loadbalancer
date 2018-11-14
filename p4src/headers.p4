/* -*- P4_16 -*- */
/* packet headers, plus the metadata struct */
#ifndef HEADERS_P4
#define HEADERS_P4


#include <core.p4>
#include <v1model.p4>

typedef bit<48> mac_addr_t;
typedef bit<9>  egressSpec_t;
typedef bit<32> ip4Addr_t;

const bit<16> TYPE_IPV4 = 0x0800;
const bit<16> TYPE_IPV6 = 0x86DD;
const bit<8>  TYPE_TCP  = 6;


header ethernet_t {
    mac_addr_t dst_addr;
    mac_addr_t src_addr;
    bit<16>    ethertype;
}

header ipv4_t {
    bit<4>    version;
    bit<4>    ihl;
    bit<8>    diffserv;
    bit<16>   totalLen;
    bit<16>   identification;
    bit<3>    flags;
    bit<13>   fragOffset;
    bit<8>    ttl;
    bit<8>    protocol;
    bit<16>   hdrChecksum;
    ip4Addr_t src_addr;
    ip4Addr_t dst_addr;
}

header tcp_t{
    bit<16> srcPort;
    bit<16> dstPort;
    bit<32> seqNo;
    bit<32> ackNo;
    bit<4>  data_offset;
    bit<4>  res;
    bit<1>  cwr;
    bit<1>  ece;
    bit<1>  urg;
    bit<1>  ack;
    bit<1>  psh;
    bit<1>  rst;
    bit<1>  syn;
    bit<1>  fin;
    bit<16> window;
    bit<16> checksum;
    bit<16> urgentPtr;
}

/* https://en.wikipedia.org/wiki/IPv6_packet */
header ipv6_t {
    bit<4>    version;
    bit<8>    traffic_class;
    bit<20>   flow_label;
    bit<16>   payload_length;
    bit<8>    next_header;
    bit<8>    hop_limit;
    bit<128>  src_addr;
    bit<128>  dst_addr;
}

struct learn_t {
   bit<48>	mac_src_addr;
   bit<16>	ingress_port;
}

struct metadata {
    learn_t	learn;
}

struct headers {
    ethernet_t   ethernet;
    ipv4_t	 ipv4;
    ipv6_t	 ipv6;
    tcp_t	 tcp;
}


#endif
