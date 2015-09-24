from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3

from ryu.topology import switches, event

class Router(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(Router,self).__init__(self,*args,**kwargs)

    @set_ev_cls(event.EventSwitchEnter)
    def add_switch(self,ev):
        pass

    @set_ev_cls(event.EventSwitchLeave)
    def delete_switch(self,ev):
        pass

    @set_ev_cls(event.EventLinkAdd)
    def add_link(self,ev):
        pass

    @set_ev_cls(event.EventLinkDelete)
    def delete_link(self,ev):
        pass

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def new_packet(self, ev):
        pass
