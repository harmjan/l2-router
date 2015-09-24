"""
This application monitors the ports of the switches
and if more than 8 mac addresses register per port
does it shut the port down.
"""

import struct

from pprint import pprint

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3

class PortSecurity(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(PortSecurity,self).__init__(self,*args,**kwargs)
        self.port_to_mac = {}

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def new_packet(self, ev):
        """The handler of a PacketIn packet"""
        # Extract the ethernet headers
        dst, src, ethernet_type = struct.unpack_from('!6s6sH', buffer(ev.msg.data), 0)

        #pprint(ev)

        # Make the key from the switch an port combination
        k = ev.msg.datapath.id, ev.msg.match['in_port']

        # If this is on a port not seen before add a new list
        if k not in self.port_to_mac:
            self.port_to_mac[k] = [src]
        # If this port is seen before see if the mac source is new
        elif src not in self.port_to_mac[k]:
            self.port_to_mac[k].append(src)
            # If there are now more than 8 mac addresses known for
            # this port shut it down
            if len(self.port_to_mac[k]) > 8:
                print "Shutting down port", ev.msg.match['in_port'], "on switch", ev.msg.datapath.id
                shutdown_port_msg = ev.msg.datapath.ofproto_parser.OFPPortMod(
                        datapath = ev.msg.datapath,
                        port_no = ev.msg.match['in_port'],
                        config = (ev.msg.datapath.ofproto.OFPPC_PORT_DOWN | ev.msg.datapath.ofproto.OFPPC_NO_RECV),
                )
                ev.msg.datapath.send_msg(shutdown_port_msg)
                #flow_mod_msg = ev.msg.datapath.ofproto_parser.OFPFlowMod(
                #        datapath = ev.msg.datapath,
                #        command = ev.msg.datapath.ofproto.OFPFC_ADD,
                #        match = ev.msg.datapath.ofproto_parser.OFPMatch(
                #            in_port = ev.msg.match['in_port']
                #        ),
                #        instructions = []
                #)
                #ev.msg.datapath.send_msg(flow_mod_msg)
