# Next steps

- [X] controller code cleanup: inheritance to the rescue!
- [X] flat loadbalancer (ECMP)
- [X] convert existing stuff into a twisted-friendly class
- [ ] make a lines protocol + a "main" for tests
- [ ] use that controller from thingy that decides weight based on something
- [ ] simple weighted loadbalancer (big bucket table)
- [ ] tests for ^^
- [ ] don't drop connections
- [ ] exploring the behavior (oscillations and stuff)
- [ ] tree thing

Not really:

- [ ] IPv6 + rewriting XD

-------------------------------------------

TODO ask on meeting:

* I should either track whether the connection is NATted (so a set membership/bloom filter)
   OR drop direct connections to backends.
* should I drop unnecessary code? (IPv6; L2 learning)

notes:

switch goes x_x / starts dropping packets at about 10kpps
