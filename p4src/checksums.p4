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
    apply {}
}

/*************************************************************************
**************   C H E C K S U M    C O M P U T A T I O N   **************
*************************************************************************/

control MyComputeChecksum(inout headers  hdr, inout metadata meta) {
    apply {}
}


#endif