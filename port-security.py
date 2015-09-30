"""
This application monitors the ports of the switches
and if more than 8 mac addresses register per port
does it shut the port down.
"""

import struct

from pprint import pprint

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3 as ofproto
from ryu.ofproto import ofproto_v1_3_parser as parser

from ryu.topology import event as topo_event

from ryu.lib.packet import packet, ethernet, ether_types

class PortSecurity(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(PortSecurity,self).__init__(self,*args,**kwargs)

        # A dictionary saving each mac to what switch and port
        # it was seen on.
        # mac => (dpid, port_no)
        self.port_to_mac = {}

        self.port_to_hw_addr = {}

    @set_ev_cls(topo_event.EventSwitchEnter)
    def add_switch(self,ev):
        for port in ev.switch.ports:
            k = ev.switch.dp.id, port.port_no
            self.port_to_hw_addr[k] = port.hw_addr

    @set_ev_cls(ofp_event.EventOFPPacketIn)
    def new_packet(self, ev):
        """The handler of a PacketIn packet"""
        # Extract the ethernet headers
        pck = packet.Packet(ev.msg.data)
        eth = pck.get_protocol(ethernet.ethernet)

        # Ignore the LLDP packets send by topology discovery
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        # Make the key from the switch an port combination
        k = ev.msg.datapath.id, ev.msg.match['in_port']

        # If this is on a port not seen before add a new list
        if k not in self.port_to_mac:
            self.port_to_mac[k] = [eth.src]
        # If this port is seen before see if the mac source is new
        elif eth.src not in self.port_to_mac[k]:
            self.port_to_mac[k].append(eth.src)
            # If there are now more than 8 mac addresses known for
            # this port shut it down
            if len(self.port_to_mac[k]) > 8:
                print "Shutting down port", ev.msg.match['in_port'], "on switch", ev.msg.datapath.id
                shutdown_port_msg = parser.OFPPortMod(
                        datapath=ev.msg.datapath,
                        port_no=ev.msg.match['in_port'],
                        hw_addr=self.port_to_hw_addr[k],
                        config=(ofproto.OFPPC_PORT_DOWN | ofproto.OFPPC_NO_RECV | ofproto.OFPPC_NO_FWD),
                        mask=(ofproto.OFPPC_PORT_DOWN | ofproto.OFPPC_NO_RECV | ofproto.OFPPC_NO_FWD)
                )
                ev.msg.datapath.send_msg(shutdown_port_msg)
