#!/usr/bin/env python

from p4utils.utils.topology import Topology
from twisted.internet import defer, task, reactor
from myutils.twisted_utils import print_method_call

from controller.sswitch_API_async_wrapper import SimpleSwitchAPIAsyncWrapper
from controller.settings import p4settings

from threading import Thread
from scapy.all import Ether, sniff, Packet, BitField

defer.setDebugging(True)


class SnifferThread(Thread):
    def __init__(self, reactor, shared_queue, iface):
        Thread.__init__(self)
        self.reactor = reactor
        self.shared_queue = shared_queue
        self.iface = iface

    @print_method_call
    def run(self):
        sniff(iface=self.iface, prn=self.consume_packet)

    def consume_packet(self, raw_packet):
        packet = Ether(str(raw_packet))
        # print('received packet: {} +++ {}'.format(packet.summary(), packet.type))

        if packet.type == p4settings['ETHERTYPE_CPU']:
            self.reactor.callFromThread(self.shared_queue.put, packet)

class BaseController(object):
    """A base P4 switch controller that your controllers probably want to inherit from.

    Implements the CPU loop. You must override the
    `recv_packet(self, packet)` method to use it.
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

    def recv_packet(self, msg):
        raise NotImplementedError(
            "Packet from switch received, but recv_packet has not been implemented")

    @defer.inlineCallbacks
    def _consume_from_packet_queue(self):
        msg = yield self.packet_queue.get()
        self.recv_packet(msg)
        reactor.callLater(0, self._consume_from_packet_queue)


    @print_method_call
    def start_sniffer_thread(self):
        self.packet_queue = defer.DeferredQueue()
        cpu_port_intf = str(self.topo.get_cpu_port_intf(self.sw_name).replace("eth0", "eth1"))
        self.sniffer_thread = SnifferThread(reactor, self.packet_queue, cpu_port_intf)
        self.sniffer_thread.daemon = True  # die when the main thread dies
        self.sniffer_thread.start()

        workers = 4
        for i in range(workers):
            self._consume_from_packet_queue()

    @defer.inlineCallbacks
    def init(self):
        """Reminder: init() is Special."""
        if self.cpu_port:
            yield self.controller.mirroring_add(p4settings['CPU_PORT_MIRROR_ID'], self.cpu_port)

    @classmethod
    def run(cls, sw_name):
        """Deprecated."""
        task.react((lambda reactor, sw_name: cls.get_initialised(sw_name)), [sw_name])


@defer.inlineCallbacks
def main(cls):
    import sys
    sw_name = sys.argv[1] if len(sys.argv) > 1 else 's1'
    cls.run(sw_name)
