from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3

from ryu.topology import switches, event

class Init(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(Init,self).__init__(self,*args,**kwargs)

    @set_ev_cls(event.EventSwitchEnter)
    def add_switch(self,ev):
        """ Switch enter event

        When a new switch is added to the network is it
        the job of the init module to delete all previous
        flows and install the table miss flows.
        """
        new_datapath = ev.switch.dp


        # Delete all previous flows in all tables, we can't
        # just delete all flows since the topology discovery
        # service also installs flows and runs before this
        # module. Instead does this controller only add rules
        # with cookie set to 1, which the following lines will
        # delete.
        for table in [0,1]:
            delete_msg = new_datapath.ofproto_parser.OFPFlowMod(
                    datapath=new_datapath,
                    table_id=table,
                    cookie=1,
                    cookie_mask=1,
                    command=new_datapath.ofproto.OFPFC_DELETE,
                    out_port=new_datapath.ofproto.OFPP_ANY,
                    out_group=new_datapath.ofproto.OFPG_ANY,
                    match=new_datapath.ofproto_parser.OFPMatch(),
                    instructions=[]
            )
            new_datapath.send_msg(delete_msg)

        # Add flowtable 0 table miss entry
        add_msg_0 = new_datapath.ofproto_parser.OFPFlowMod(
                datapath=new_datapath,
                table_id=0,
                priority=0,
                cookie=1,
                command=new_datapath.ofproto.OFPFC_ADD,
                match=new_datapath.ofproto_parser.OFPMatch(),
                instructions=[
                    new_datapath.ofproto_parser.OFPInstructionGotoTable(1),
                    new_datapath.ofproto_parser.OFPInstructionActions(
                        type_=new_datapath.ofproto.OFPIT_WRITE_ACTIONS,
                        actions=[new_datapath.ofproto_parser.OFPActionGroup(group_id=0)]
                    )
                ]
        )
        new_datapath.send_msg(add_msg_0)

        # Add flowtable 1 table miss entry
        add_msg_1 = new_datapath.ofproto_parser.OFPFlowMod(
                datapath=new_datapath,
                table_id=1,
                priority=0,
                cookie=1,
                command=new_datapath.ofproto.OFPFC_ADD,
                match=new_datapath.ofproto_parser.OFPMatch(),
                instructions=[
                    new_datapath.ofproto_parser.OFPInstructionActions(
                        type_=new_datapath.ofproto.OFPIT_APPLY_ACTIONS,
                        actions=[new_datapath.ofproto_parser.OFPActionOutput(new_datapath.ofproto.OFPP_CONTROLLER)]
                    )
                ]
        )
        new_datapath.send_msg(add_msg_1)
