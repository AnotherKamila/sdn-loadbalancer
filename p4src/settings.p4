/* -*- P4_16 -*- */
/* table sizes, register widths, and such */
#ifndef SETTINGS_P4
#define SETTINGS_P4


#include <core.p4>
#include <v1model.p4>

#define ARP_TABLE_SIZE       256
#define ROUTING_TABLE_SIZE  1024
#define VIP_TABLE_SIZE       256
#define DIP_TABLE_SIZE      4096
#define CONN_TABLE_SIZE    16384

#define TABLE_VERSIONS_SIZE 2

// 2 ^ TABLE_VERSIONS_SIZE
#define MAX_TABLE_VERSIONS  4

// https://hur.st/bloomfilter/?n=100&p=1.0E-5&m=&k=4
#define BLOOM_FILTER_ENTRIES 8192

#define CPU_PORT_MIRROR_ID 100
#define ETHERTYPE_CPU      0xbeef


#endif
