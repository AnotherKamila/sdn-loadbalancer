To avoid going crazy, I structure stuff into classes based (more or less) on layer. Each layer is quite decoupled from the other layers and can be thought about, debugged and tested separately.

I use inheritance to compose the controllers: for example, `Router` (which handles everything up to L3) inherits from `IPv4Routing` (provides the routing table only), `ArpLazy` (provides the ARP table only), and `L2SwitchLazy` (provides the MAC table only), plus `BaseController`. 

All controllers inherit from `base_controller.BaseController` and may override its `init` and `recv_packet` methods.

The controllers often have tests named after them in `../test/`.

I use Twisted: see `../twisted-intro.md` for a quick run through the things you need to know to read the code.
