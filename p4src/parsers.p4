/* -*- P4_16 -*- */
/* parser and deparser */
#ifndef PARSERS_P4
#define PARSERS_P4


#include <core.p4>
#include <v1model.p4>

#include "headers.p4"

/*************************************************************************
************************* P A R S E R  ***********************************
*************************************************************************/

parser MyParser(packet_in packet,
                out       headers hdr,
                inout     metadata meta,
                inout     standard_metadata_t standard_metadata) {

    state start {
        transition parse_ethernet;
    }

    state parse_ethernet {
        packet.extract(hdr.ethernet);
        transition accept;
    }
}

/*************************************************************************
************************  D E P A R S E R  *******************************
*************************************************************************/

control MyDeparser(packet_out packet, in headers hdr) {
    apply {
        packet.emit(hdr.ethernet);
    }
}


#endif