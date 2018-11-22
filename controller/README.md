To avoid going crazy, I structure stuff into classes based (more or less) on layer.
Inheritance and mixins are friends.

My convention here is that mixins are things that only do stuff on `init`. If something needs to receive messages and change tables at runtime (after the initial table filling), then it is not a mixin. But actually TODO rethink this convention.

All controllers probably want to inherit from `base_controller.BaseController` and override its `init` and `recv_msg_digest` methods.

The controllers often have tests named after them in `../test/`.
