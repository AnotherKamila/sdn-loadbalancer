# Abstract

# Introduction

L4 load-balancers enable horizontal scaling of traffic for a service across
multiple application servers.
They do so by mapping a _virtual IP_ (VIP) to a pool of _direct IPs_ (DIPs), or
the actual application servers: when a request arrives to the VIP, the load
balancer forwards it to one of the multiple servers in the DIP pool.
This is critical to performance, especially for large services, because with
load balancing what appears to be a single endpoint can process more requests at
the same time.
However, the load balancer quickly becomes a bottleneck: a high-end software
load balancer can forward up to 12 Mpps, while the underlying network throughput
can easily reach multiple Gpps.\ref{maglev}

Furthermore, load balancers typically select servers from the pool
uniformly, which can pose problems in multiple scenarios.
If the servers are heterogeneous, whether it is because of a different hardware
configuration, or because they run multiple different applications (as is often
the case in datacenters), uniformly distributed requests often do not correspond
to uniformly distributed load. It would be very useful to take into account some
server metrics, such as server load or mean request latency, when making load
balancing decisions.

Therefore, this project proposes an SDN-based load balancer able to load-balance
entirely in the data plane (i.e. at line rates**, which can additionally forward
the requests to the application servers with an arbitrary dynamically adjustable
distribution.
The distribution can then be derived at real-time from application server
metrics such as server load or request latency.

# Background and related work

L4 load balancing in general works as follows:

1. Match the packet's destination IP and destination port against the load
   balancer's Virtual IPs and map to a server pool.
2. Select a DIP from the pool. This can be done e.g. in a round-robin fashion,
   or by hashing the fivetuple. The usual approaches result in a uniform
   distribution of requests to servers.
3. Re-write the destination IP and port.
4. Forward the packet to the selected server.
5. Make sure to handle the return path correctly: rewrite the source IP and port
   back to the Virtual IP on replies for this request.

The challenge when implementing an SDN-based load balancer is **per-connection
consistency**, i.e. making sure that all packets of a given connection are
forwarded to the same application server.
Unlike in software, a hardware-based load balancer cannot afford to
keep much state (because that would reduce performance), and therefore it is not
trivial to ensure that all packets of the same connection will be forwarded to
the same server when the pool changes.
Pool changes are quite frequent, as especially in large datacenters servers come
offline or online multiple times per second.\ref{whyisthereatypointhispaperstitle}

SDN-based load balancing has been explored in \ref{silkroad}. The paper focused
on performance, scalability, and the ability to handle frequent changes to the
DIP pools.
The approach in this paper is highly optimised and rather clever.
While their way of ensuring per-connection consistency has a better memory
footprint than ours, we found it valuable to create a simpler approach.
We enjoyed seeing how SDN enables solving the same problem in very different
ways, with different tradeoffs.

To our knowledge, SDN-based load balancing with an adjustable distribution has not been explored before.

# Implementation

## Up to L3: A simple router

## Simple L4 load balancer

## Dynamically adjusting weights

# Evaluation

# Conclusion

# References

TODO bibtexify

maglev: D. E. Eisenbud, et al. 2016. Maglev: A Fast and Reliable Software Network Load Balancer. In NSDI.
silkroad: SilkRoad: Making Stateful Layer-4 Load Balancing Fast and Cheap Using Switching ASICs
whyisthereatypointhispaperstitle: R. Govindan, et al. Evolve or Die: High-Availability Design Principles Drawn from Googles Network Infrastructure. In ACM SIGCOMM 2016.
