/* -*- P4_16 -*- */
/* checksum verification and computation */
#ifndef CHECKSUMS_P4
#define CHECKSUMS_P4


#include <core.p4>
#include <v1model.p4>

#include "headers.p4"

/*************************************************************************
*************   C H E C K S U M    V E R I F I C A T I O N   *************
*************************************************************************/

control MyVerifyChecksum(inout headers hdr, inout metadata meta) {
    apply {} // :D
}

/*************************************************************************
**************   C H E C K S U M    C O M P U T A T I O N   **************
*************************************************************************/

control MyComputeChecksum(inout headers  hdr, inout metadata meta) {
    apply {
        update_checksum(
            hdr.ipv4.isValid(),
            {
                hdr.ipv4.version,
                hdr.ipv4.ihl,
                hdr.ipv4.diffserv,
                hdr.ipv4.total_len,
                hdr.ipv4.identification,
                hdr.ipv4.flags,
                hdr.ipv4.frag_offset,
                hdr.ipv4.ttl,
                hdr.ipv4.protocol,
                hdr.ipv4.src_addr,
                hdr.ipv4.dst_addr 
            },
            hdr.ipv4.hdr_checksum,
            HashAlgorithm.csum16
        );
        // TODO TCP checksum over v6 is different :-/
        // Note: the following does not support TCP options.
        update_checksum_with_payload(
            hdr.tcp.isValid() && hdr.ipv4.isValid(),
            {
                hdr.ipv4.src_addr,
                hdr.ipv4.dst_addr,
                8w0,
                hdr.ipv4.protocol,
                meta.l4_payload_length,
                hdr.tcp.src_port,
                hdr.tcp.dst_port,
                hdr.tcp.seq_no,
                hdr.tcp.ack_no,
                hdr.tcp.data_offset,
                hdr.tcp.res,
                hdr.tcp.flags,
                hdr.tcp.window,
                hdr.tcp.urgent_ptr
            },
            hdr.tcp.checksum,
            HashAlgorithm.csum16
        );
    }
}


#endif