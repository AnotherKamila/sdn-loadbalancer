# Next steps

- [X] controller code cleanup: inheritance to the rescue!
- [X] flat loadbalancer (ECMP)
- [X] convert existing stuff into a twisted-friendly class
- [X] make testing arbitrary scenarios easier
- [X] tests for weighted
- [ ] simple weighted loadbalancer (big bucket table)
- [ ] don't drop connections
- [ ] tree thing
- [ ] exploring the behavior (oscillations and stuff)
- [ ] use that controller from thingy that decides weight based on something

Not really / not worth it:

- [ ] IPv6 + rewriting XD
- [ ] I should either track whether the connection is NATted (so a set membership/bloom filter)
        OR drop direct connections to backends.

## TODO ask on meeting:

* report: when?
* presentation: how long?

## Notes:

* switch goes x_x / starts dropping packets at about 10kpps

# Report


# Presentation
