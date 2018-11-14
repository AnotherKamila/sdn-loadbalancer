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

    action forward(bit<9> port) {
        standard_metadata.egress_spec = port;
    }

    action set_mcast_grp(bit<16> group){
	standard_metadata.mcast_grp = group;
    }

    action mac_learn (){
	meta.learn.mac_src_addr = hdr.ethernet.src_addr;
	meta.learn.ingress_port = (bit<16>) standard_metadata.ingress_port;
		
    }
    table smac {
         key = {hdr.ethernet.src_addr: exact;}

         actions = {
		NoAction;
		mac_learn;
         }
         default_action = mac_learn;
//TODO should we set some table size or don't set this value at all?
         //size = DEFAULT_TABLE_SIZE;
     }

    table dmac {
         key = {hdr.ethernet.dst_addr: exact;}

         actions = {
                forward;
		NoAction;
         }
         default_action = NoAction;
     }


    table broadcast {
         key = {standard_metadata.ingress_port: exact;}

         actions = {
		set_mcast_grp;
         }
     }

    apply {
	smac.apply();
	if(dmac.apply().hit){
		//
	} else {
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
