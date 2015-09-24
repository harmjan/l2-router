"""
This application maintains a broadcast tree in a
group table bucket. Forwarding packets to this bucket
on every switch will flood those packets safely over
the network without packets getting stuck in a loop.
"""

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3

from ryu.topology import switches, event

class Broadcast(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

# Using the _CONTEXTS mechanism is discouraged in the
# ryu documentation
#    _CONTEXTS = {
#            'topology': switches.Switches
#    }

    def __init__(self, *args, **kwargs):
        super(Broadcast,self).__init__(self,*args,**kwargs)

        # A dictionary from datapath id to a list of connected neighbours
        self.switches = {}

    @set_ev_cls(event.EventSwitchEnter)
    def add_switch(self,ev):
        self.switches[ev.switch.dp.id] = []
        self.set_broadcast_tree()

    @set_ev_cls(event.EventSwitchLeave)
    def delete_switch(self,ev):
        del self.switches[ev.switch.dp.id]
        self.set_broadcast_tree()

    @set_ev_cls(event.EventLinkAdd)
    def add_link(self,ev):
        if ev.link.src.dpid in self.switches:
            tmp = ev.link.src.port_no, ev.link.dst.dpid, ev.link.dst.port_no
            self.switches[ev.link.src.dpid].append(tmp)
            self.set_broadcast_tree()

    @set_ev_cls(event.EventLinkDelete)
    def delete_link(self,ev):
        if ev.link.src.dpid in self.switches:
            tmp = ev.link.src.port_no, ev.link.dst.dpid, ev.link.dst.port_no
            self.switches[ev.link.src.dpid].remove(tmp)
            self.set_broadcast_tree()

    def set_broadcast_tree(self):
        """ Calculate and set a broadcast tree

        A broadcast tree is calculated and set in the
        connected openflow switches.
        """

        # FIXME set tree in the openflow switches

        # Clear the previous group

        # Use a barrier to make sure that happens

        st = self.calculate_spanning_tree()

        print "New tree"
        for k,v in st.items():
            print k, ": [ ",
            for i in v:
                print i,
            print "]"

        # Create the new group

    def calculate_spanning_tree(self):
        """ Calculate a spanning tree

        A spanning tree is calculated from the switch
        information recorded from the ryu events. The
        spanning tree is returned as an dictionary from
        datapath id to all the ports that should be
        forwarded to on that datapath to flood a message.
        """
        # The set of currently reachable datapaths
        reachable  = set()
        # The dpid's that still can be explored
        explorable = []
        # The list of ports to forward on in the format
        # dpid => [port, ...]
        flood_ports = {}

        if len(self.switches) == 0:
            return flood_ports

        # Pick an initial datapath
        dpid, _ = self.switches.iteritems().next()
        reachable.add(dpid)
        explorable.append(dpid)
        flood_ports[dpid] = []

        # Explore the graph breadth first from the initial datapath
        while len(explorable) != 0:
            src_dpid = explorable.pop()
            for src_port, dst_dpid, dst_port in self.switches[dpid]:
                if dst_dpid not in reachable:
                    reachable.add(dst_dpid)
                    explorable.append(dst_dpid)
                    flood_ports[dst_dpid] = [dst_port]
                    flood_ports[src_dpid].append(src_port)

        # FIXME This only works on completely connected components

        return flood_ports
