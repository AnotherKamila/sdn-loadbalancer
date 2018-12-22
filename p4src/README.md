# P4 program

Things in here:

* `main-unversioned.p4`: simple load balancer without versioned tables
* `main.p4` is the complete program of the full load balancer
* `settings.p4`: compile-time constants. I parse this file from Python too, so that the controller knows the compile-time settings.
* the rest should be self-explanatory

## Control flow

See the report for a detailed description of how this works. For reference, here is the control flow diagram:

![life of a packet](./life-of-a-packet.svg)

TODO the bigger one

This diagram hopefully helps clarify the `apply {}` block in `main.p4`.
