from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet
from ryu.topology import event
from ryu.topology.api import get_switch, get_link

class ReconfigController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(ReconfigController, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.topology_api_app = self

    def delete_flows(self, datapath):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        match = parser.OFPMatch()
        mod = parser.OFPFlowMod(
            datapath=datapath,
            command=ofproto.OFPFC_DELETE,
            out_port=ofproto.OFPP_ANY,
            out_group=ofproto.OFPG_ANY,
            priority=1,
            match=match
        )
        datapath.send_msg(mod)

    def reconfigure(self):
        print("\n⚠️  Topology change detected → Reconfiguring...")
        print("🔄 Clearing all flows and MAC tables\n")

        self.mac_to_port.clear()

        for dp in self.dps.values():
            self.delete_flows(dp)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        if not hasattr(self, 'dps'):
            self.dps = {}
        self.dps[datapath.id] = datapath

    @set_ev_cls(event.EventLinkDelete)
    def link_delete_handler(self, ev):
        print("❌ Link Removed → Trigger Reconfiguration")
        self.reconfigure()

    @set_ev_cls(event.EventLinkAdd)
    def link_add_handler(self, ev):
        print("✅ Link Added")

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto

        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)

        dst = eth.dst
        src = eth.src
        in_port = msg.match['in_port']

        self.mac_to_port[dpid][src] = in_port

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst)
            mod = parser.OFPFlowMod(
                datapath=datapath,
                priority=1,
                match=match,
                instructions=[parser.OFPInstructionActions(
                    ofproto.OFPIT_APPLY_ACTIONS, actions)]
            )
            datapath.send_msg(mod)

        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=msg.buffer_id,
            in_port=in_port,
            actions=actions,
            data=msg.data
        )
        datapath.send_msg(out)
