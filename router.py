from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3

from ryu.topology import switches, event

from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types

from collections import deque

class Router(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(Router,self).__init__(self,*args,**kwargs)

        # A dictionary translating dpid to class Datapath
        # dpid => class Datapath
        self.switches = {}

        # A dictionary containing all the links a switch
        # has to other switches. The port saved is the port
        # on the other switch connected to this switch.
        # dpid => [(dpid,port_no), ...]
        self.switch_graph = {}

        # A dictionary containing all the mac addresses
        # that were learned plus where they are located
        # mac => (dpid,port_no)
        self.learned_macs = {}

        # The saved outputs from the bfs algorithm
        # dpid => {dpid => port}
        self.saved_bfs = {}

    @set_ev_cls(event.EventSwitchEnter)
    def add_switch(self,ev):
        if ev.switch.dp.id not in self.switches:
            self.switches[ev.switch.dp.id] = ev.switch.dp
            self.switch_graph[ev.switch.dp.id] = []

    @set_ev_cls(event.EventSwitchLeave)
    def remove_switch(self,ev):
        if ev.switch.dp.id in self.switches:
            del self.switches[ev.switch.dp.id]
            del self.switch_graph[ev.switch.dp.id]

    @set_ev_cls(event.EventLinkAdd)
    def add_link(self,ev):
        if ev.link.src.dpid in self.switches:
            # Add the link src => dst
            tmp = ev.link.dst.dpid, ev.link.dst.port_no
            self.switch_graph[ev.link.src.dpid].append(tmp)

        if ev.link.dst.dpid in self.switches:
            # Add the link dst => src
            tmp = ev.link.src.dpid, ev.link.src.port_no
            self.switch_graph[ev.link.dst.dpid].append(tmp)

        self.saved_bfs.clear()

    @set_ev_cls(event.EventLinkDelete)
    def remove_link(self,ev):
        if ev.link.src.dpid in self.switches:
            tmp = ev.link.dst.dpid, ev.link.dst.port_no
            self.switch_graph[ev.link.src.dpid] = filter( lambda a: a!=tmp, self.switch_graph[ev.link.src.dpid] )

        if ev.link.dst.dpid in self.switches:
            tmp = ev.link.src.dpid, ev.link.src.port_no
            self.switch_graph[ev.link.dst.dpid] = filter( lambda a: a!=tmp, self.switch_graph[ev.link.dst.dpid] )

        self.saved_bfs.clear()

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def new_packet(self, ev):
        pck = packet.Packet(ev.msg.data)
        eth = pck.get_protocol(ethernet.ethernet)

        # Ignore the LLDP packets send by topology discovery
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        if ev.msg.datapath.id not in self.switches:
            return

        if eth.src not in self.learned_macs:
            print "New mac address", eth.src
            self.learned_macs[eth.src] = ev.msg.datapath.id, ev.msg.match['in_port']
            self.add_routes(ev.msg.datapath, ev.msg.match['in_port'], eth.src)
        else:
            print "Received packetin with src mac I already know", eth.src
            dpid, port = self.learned_macs[eth.src]
            if port != ev.msg.match['in_port'] or dpid != ev.msg.datapath.id:
                print "\tReceived known mac",eth.src,"on different port!"

    def add_routes(self, datapath, local_port, mac):
        """ Add the routes to all switches when a new mac is learned """
        # Add the route to the switch the device is connected to
        local_route = datapath.ofproto_parser.OFPFlowMod(
                datapath=datapath,
                table_id=0,
                priority=20,
                cookie=1,
                command=datapath.ofproto.OFPFC_ADD,
                match=datapath.ofproto_parser.OFPMatch( eth_dst=mac ),
                instructions=[
                    datapath.ofproto_parser.OFPInstructionGotoTable(1),
                    datapath.ofproto_parser.OFPInstructionActions(
                        type_=datapath.ofproto.OFPIT_WRITE_ACTIONS,
                        actions=[datapath.ofproto_parser.OFPActionOutput(local_port)]
                    )
                ]
        )
        datapath.send_msg(local_route)

        # Now add routes to all other switches that can get there
        bfs = self.breadth_first_search(datapath.id)
        for dpid,port in bfs.iteritems():
            dp = self.switches[dpid]
            foreign_route = dp.ofproto_parser.OFPFlowMod(
                    datapath=dp,
                    table_id=0,
                    priority=10,
                    cookie=1,
                    command=dp.ofproto.OFPFC_ADD,
                    match=dp.ofproto_parser.OFPMatch( eth_dst=mac ),
                    instructions=[
                        dp.ofproto_parser.OFPInstructionActions(
                            type_=dp.ofproto.OFPIT_WRITE_ACTIONS,
                            actions=[dp.ofproto_parser.OFPActionOutput(port)]
                        )
                    ]
            )
            dp.send_msg(foreign_route)

        # Add the route to table 1 so we don't get messages about
        # this mac address anymore
        for dp in self.switches.values():
            block_route = dp.ofproto_parser.OFPFlowMod(
                    datapath=dp,
                    table_id=1,
                    priority=20,
                    cookie=1,
                    command=dp.ofproto.OFPFC_ADD,
                    match=dp.ofproto_parser.OFPMatch( eth_src=mac ),
                    instructions=[]
            )
            dp.send_msg(block_route)

    def breadth_first_search(self,start_switch_id):
        """ Calculate a route for all switches to switch_id

        The result is returned in a dictionary from each
        datapath id to the port it should forward on to get
        to the passed switch id.
        dpid => forward_port

        The original start_switch_id is not available in this
        dictionary.
        """

        # Look up if we have already computed a bfs
        # from this start node
        if start_switch_id in self.saved_bfs:
            return self.saved_bfs[start_switch_id]

        # The queue with nodes to explore
        q = deque([start_switch_id])

        # The set with switch id's that are already explored
        explored = set([start_switch_id])

        # The resulting routes in a dictionary with the ports
        # for each switch to forward to
        # dpid => forward_port
        forward_port = {}

        while len(q) != 0:
            node = q.popleft()
            explored.add(node)

            # Loop over the neighbours
            for dpid,port in self.switch_graph[node]:
                if dpid not in explored:
                    forward_port[dpid] = port
                    explored.add(dpid)
                    q.append(dpid)

        # Cache the result
        self.saved_bfs[start_switch_id] = forward_port

        return forward_port
