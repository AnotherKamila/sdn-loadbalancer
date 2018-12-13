# Next steps

- [X] controller code cleanup: inheritance to the rescue!
- [X] flat loadbalancer (ECMP)
- [X] convert existing stuff into a twisted-friendly class
- [X] make testing arbitrary scenarios easier
- [ ] don't drop connections
- [ ] send new connection packets to CPU & read them there & fill out conn_table
- [ ] old versions Bloom filters
- [X] tests for weighted
- [ ] simple weighted loadbalancer (big bucket table)
- [ ] use that controller from thingy that decides weight based on something
- [ ] exploring the behavior / producing shiny graphs
- [ ] tree thing

Not really / not worth it:

- [ ] IPv6 + rewriting XD
- [ ] I should either track whether the connection is NATted (so a set membership/bloom filter)
        OR drop direct connections to backends.

## TODO ask on meeting:

* report: when?
* presentation: how long?

## Notes:

* switch goes x_x / starts dropping packets at about 10kpps
* sniffing as non root with python: `$ sudo setcap cap_net_raw=eip $(which python)`

# Interesting problems

## something something

### 1. How to assign weights

=> put the server there 5 times instead of one
=> more interesting idea (not implemented / future work): prefix tree thingy

### 2. Which weights to assign

=> control theory / not interesting from SDN viewpoint
=> in our case: simple function of current load

### 3. How do I dynamically change the weights without dropping connections?

=> Bloom filter magic + conn_table:

1. conn_table
2. it takes a while to write into conn_table and packets are coming in => old versions + Bloom filters

# Report


# Presentation
