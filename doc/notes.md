# Next steps

- [X] controller code cleanup: inheritance to the rescue!
- [X] flat loadbalancer (ECMP)
- [ ] simple weighted loadbalancer (big bucket table)
- [ ] tests for ^^ + exploring the behavior (oscillations and stuff)
- [ ] don't drop connections
- [ ] use more CPU and less memory
- [ ] how to update weights in ^^ ?
- [ ] don't drop connections (again)
- [ ] IPv6 + rewriting XD

-------------------------------------------

TODO ask on meeting:

* I should either track whether the connection is NATted (so a set membership/bloom filter)
   OR drop direct connections to backends.
* should I drop unnecessary code? (IPv6; L2 learning)
