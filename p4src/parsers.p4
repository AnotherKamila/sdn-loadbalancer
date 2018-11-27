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

        packet.extract(hdr.ethernet);
        transition select(hdr.ethernet.ethertype){
            TYPE_IPV4: ipv4;
            TYPE_IPV6: ipv6;
            default: accept;
        }
    }

    state ipv4 {
        packet.extract(hdr.ipv4);
        meta.l4_payload_length = hdr.ipv4.total_len - (((bit<16>)hdr.ipv4.ihl) << 2);
 
        transition select(hdr.ipv4.protocol){
            TYPE_TCP: tcp;
            default: accept;
        }
    }

    state ipv6 {
        packet.extract(hdr.ipv6);
        // TODO meta.l4_payload_length

        transition select(hdr.ipv6.next_header){
            TYPE_TCP: tcp;
            default: accept;
        }
    }

    state tcp {
       packet.extract(hdr.tcp);
       transition accept;
    }

}

/*************************************************************************
************************  D E P A R S E R  *******************************
*************************************************************************/

control MyDeparser(packet_out packet, in headers hdr) {
    apply {
        packet.emit(hdr.ethernet);

        // will do either - the ingress/packet.emit() emits only if the header
        // is valid, so our code must ensure that exactly one of ipv4, ipv6
        // headers is valid (use packet.setValid()/packet.setInvalid())
        packet.emit(hdr.ipv4);
        packet.emit(hdr.ipv6);
        packet.emit(hdr.tcp);
    }
}


#endif
