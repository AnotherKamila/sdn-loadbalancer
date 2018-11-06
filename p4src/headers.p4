/* -*- P4_16 -*- */
/* packet headers, plus the metadata struct */
#ifndef HEADERS_P4
#define HEADERS_P4


#include <core.p4>
#include <v1model.p4>

typedef bit<48> mac_addr_t;

header ethernet_t {
    mac_addr_t dst_addr;
    mac_addr_t src_addr;
    bit<16>    ethertype;
}

struct metadata {
}

struct headers {
    ethernet_t   ethernet;
}


#endif