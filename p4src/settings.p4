/* -*- P4_16 -*- */
/* table sizes, register widths, and such */
#ifndef SETTINGS_P4
#define SETTINGS_P4


#include <core.p4>
#include <v1model.p4>

#define ARP_TABLE_SIZE      256
#define ROUTING_TABLE_SIZE 1024
#define VIP_TABLE_SIZE      256
#define DIP_TABLE_SIZE     1024
#define CONN_TABLE_SIZE    8192

// https://hur.st/bloomfilter/?n=100&p=1.0E-5&m=&k=4
#define VERSION_BLOOM_FILTER_ENTRIES 8192


#endif
