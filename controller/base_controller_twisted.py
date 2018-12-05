#!/usr/bin/env python

from p4utils.utils.topology import Topology
from twisted.internet import defer, task

from controller.sswitch_API_async_wrapper import SimpleSwitchAPIAsyncWrapper

defer.setDebugging(True)


class BaseController(object):
    """A base P4 switch controller that your controllers probably want to inherit from.

    Currently implements neither the CPU nor the digest loop.

    CPU loop would be easy to add.
    """

    def __init__(self, sw_name, topology_db_file="./topology.db"):
        self.topo = Topology(db=topology_db_file)
        # print(self.topo)
        self.sw_name = sw_name
        self.thrift_port = self.topo.get_thrift_port(sw_name)
        self.cpu_port =  self.topo.get_cpu_port_index(self.sw_name)
        self.controller = SimpleSwitchAPIAsyncWrapper(self.thrift_port)

    @classmethod
    @defer.inlineCallbacks
    def get_initialised(cls, sw_name, *args, **kwargs):
        obj = cls(sw_name, *args, **kwargs)
        yield obj._before_init()

        # This is horrible and I probably shouldn't be doing it.
        # FIXME actually, this is really terrible and I _really_ shouldn't be
        # doing it, because it breaks expectations.
        for mcls in reversed(cls.__mro__):
            if 'init' in mcls.__dict__:
                yield defer.maybeDeferred(mcls.init, obj)

        defer.returnValue(obj)

    def _before_init(self):
        return self.controller.reset_state()

    def init(self):
        """Reminder: init() is Special."""
        pass

    @classmethod
    def run(cls, sw_name):
        task.react((lambda reactor, sw_name: cls.get_initialised(sw_name)), [sw_name])


@defer.inlineCallbacks
def main(cls):
    import sys
    sw_name = sys.argv[1] if len(sys.argv) > 1 else 's1'
    cls.run(sw_name)
