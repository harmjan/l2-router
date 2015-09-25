from ryu.base import app_manager
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3

from ryu.topology import event

class Broadcast(app_manager.RyuApp):
    """
    This application maintains a broadcast tree in a
    group table bucket. Forwarding packets to this bucket
    on every switch will flood those packets safely over
    the network without packets getting stuck in a loop.
    """

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(Broadcast,self).__init__(self,*args,**kwargs)

        # A dictionary from datapath id to a list of neighbour switches
        # src_dpid => [(src_port,dst_dpid,dst_port), ...]
        self.switch_graph = {}

        # A dictionary with all the ports that are not
        # connected to a switch
        # dpid => [port_no, ..]
        self.switch_ports = {}

        # A dictionary from switch dpid to switch object
        # dpid => class Datapath)
        self.switches = {}

    @set_ev_cls(event.EventSwitchEnter)
    def add_switch(self,ev):
        print "Switch added", ev.switch.dp.id

        group_msg = ev.switch.dp.ofproto_parser.OFPGroupMod(
                datapath=ev.switch.dp,
                command=ev.switch.dp.ofproto.OFPGC_ADD,
                type_=ev.switch.dp.ofproto.OFPGT_ALL,
                group_id=0
        )
        ev.switch.dp.send_msg(group_msg)

        if ev.switch.dp.id not in self.switch_graph:
            self.switch_graph[ev.switch.dp.id] = []
            self.switch_ports[ev.switch.dp.id] = [port.port_no for port in ev.switch.ports]
            self.switches[ev.switch.dp.id] = ev.switch.dp

    @set_ev_cls(event.EventSwitchLeave)
    def remove_switch(self,ev):
        print "Switch removed", ev.switch.dp.id

        if ev.switch.dp.id in self.switch_graph:
            del self.switch_graph[ev.switch.dp.id]
            del self.switch_ports[ev.switch.dp.id]
            del self.switches[ev.switch.dp.id]

            # Filter all connection that go to this switch, link down
            # events lag behind switch removal
            for key in self.switch_graph:
                self.switch_graph[key] = filter(lambda x: x[1]!=ev.switch.dp.id, self.switch_graph[key])

            self.set_broadcast_tree()

    @set_ev_cls(event.EventLinkAdd)
    def add_link(self,ev):
        print "Link added", ev.link.src.dpid, "=>", ev.link.dst.dpid

        if ev.link.src.dpid in self.switch_graph:
            tmp = ev.link.src.port_no, ev.link.dst.dpid, ev.link.dst.port_no
            self.switch_graph[ev.link.src.dpid].append(tmp)

            self.switch_ports[ev.link.src.dpid] = filter(lambda a: a!=ev.link.src.port_no, self.switch_ports[ev.link.src.dpid])
            self.switch_ports[ev.link.dst.dpid] = filter(lambda a: a!=ev.link.dst.port_no, self.switch_ports[ev.link.dst.dpid])

            self.set_broadcast_tree()

    @set_ev_cls(event.EventLinkDelete)
    def remove_link(self,ev):
        print "Link removed", ev.link.src.dpid, "=>", ev.link.dst.dpid

        if ev.link.src.dpid in self.switch_graph:
            tmp = ev.link.src.port_no, ev.link.dst.dpid, ev.link.dst.port_no
            self.switch_graph[ev.link.src.dpid] = filter(lambda x: x!=tmp,self.switch_graph[ev.link.src.dpid])

            if ev.link.src.dpid in self.switch_ports and ev.link.src.port_no not in self.switch_ports[ev.link.src.dpid]:
                self.switch_ports[ev.link.src.dpid].append(ev.link.src.port_no)
            if ev.link.dst.dpid in self.switch_ports and ev.link.dst.port_no not in self.switch_ports[ev.link.dst.dpid]:
                self.switch_ports[ev.link.dst.dpid].append(ev.link.dst.port_no)

            self.set_broadcast_tree()

    @set_ev_cls(event.EventPortAdd)
    def add_port(self,ev):
        print "Port", ev.port.port_no, "added to switch", ev.port.dpid

        self.switch_ports[ev.port.dpid].append(ev.port.port_no)

        self.set_broadcast_tree()

    @set_ev_cls(event.EventPortDelete)
    def remove_port(self,ev):
        print "Port", ev.port.port_no, "removed from switch", ev.port.dpid

        self.switch_ports[ev.port.dpid] = filter(lambda x: x!=ev.port.port_no, self.switch_ports[ev.port.dpid])

        self.set_broadcast_tree()



    def set_broadcast_tree(self):
        """ Calculate and set a broadcast tree

        A broadcast tree is calculated and set in the
        connected openflow switches
        """

        # Extract the spanning tree from the saved information
        spanning_tree = self.calculate_spanning_tree()
        # Add the normal ports
        for dpid in spanning_tree:
            spanning_tree[dpid] += self.switch_ports[dpid]

        # Update the group buckets in the switches
        for dpid, dp in self.switches.items():
            group_msg = dp.ofproto_parser.OFPGroupMod(
                    datapath=dp,
                    command=dp.ofproto.OFPGC_MODIFY,
                    type_=dp.ofproto.OFPGT_ALL,
                    group_id=0,
                    buckets=[dp.ofproto_parser.OFPBucket(actions=[dp.ofproto_parser.OFPActionOutput(port)]) for port in spanning_tree[dpid]]
            )
            dp.send_msg(group_msg)

    def calculate_spanning_tree(self):
        """ Calculate a spanning tree

        Using kruskal's algorithm extract a spanning
        tree from the graph and return it in a dictionary
        using the format:
        dpid => [port_no, ...]

        This function only finds the ports connected to
        switches it should use, all other ports that exist
        on the switch should be added afterwards.
        """
        flood_ports = {}

        class disjoint_set:
            """ A quick disjoint-set implementation """
            def __init__(self):
                self.d_set = {}

            def make_set(self,dpid):
                self.d_set[dpid] = dpid

            def find(self,dpid):
                while self.d_set[dpid] != dpid:
                    dpid = self.d_set[dpid]
                return dpid

            def same_set(self,dpid1,dpid2):
                return self.find(dpid1) == self.find(dpid2)

            def union(self,dpid1,dpid2):
                self.d_set[self.find(dpid1)] = self.find(dpid2)

        s = disjoint_set()

        # Add all switches to the disjoint-set
        for dpid in self.switch_graph:
            s.make_set(dpid)
            flood_ports[dpid] = []

        # Execute kruskal and add the ports on the edges
        # that are used to the flood_ports dictionary
        for src_dpid in self.switch_graph:
            for src_port, dst_dpid, dst_port in self.switch_graph[src_dpid]:
                if not s.same_set(src_dpid,dst_dpid):
                    s.union(src_dpid,dst_dpid)
                    flood_ports[src_dpid].append(src_port)
                    flood_ports[dst_dpid].append(dst_port)

        return flood_ports
