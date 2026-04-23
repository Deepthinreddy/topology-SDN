from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3

from ryu.topology import event
from ryu.topology.api import get_switch


class TopologyDetector(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(TopologyDetector, self).__init__(*args, **kwargs)

        self.switches = set()
        self.links = set()
        self.dps = {}   # datapaths
        self.reconfiguring = False

    # -------------------------------
    # TRACK SWITCHES (DATAPATHS)
    # -------------------------------
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        dp = ev.msg.datapath
        self.dps[dp.id] = dp

    # -------------------------------
    # SWITCH EVENTS
    # -------------------------------
    @set_ev_cls(event.EventSwitchEnter)
    def switch_enter_handler(self, ev):
        switch_list = get_switch(self, None)
        self.switches = set([s.dp.id for s in switch_list])
        self.print_topology("Switch Added")

    @set_ev_cls(event.EventSwitchLeave)
    def switch_leave_handler(self, ev):
        switch_list = get_switch(self, None)
        self.switches = set([s.dp.id for s in switch_list])
        self.print_topology("Switch Removed")

    # -------------------------------
    # LINK ADD
    # -------------------------------
    @set_ev_cls(event.EventLinkAdd)
    def link_add_handler(self, ev):
        src = ev.link.src.dpid
        dst = ev.link.dst.dpid

        link = (src, dst)
        rev = (dst, src)

        if link in self.links or rev in self.links:
            return

        self.links.add(link)
        self.print_topology("Link Added")

    # -------------------------------
    # LINK DELETE (SAFE)
    # -------------------------------
    @set_ev_cls(event.EventLinkDelete)
    def link_delete_handler(self, ev):
        src = ev.link.src.dpid
        dst = ev.link.dst.dpid

        link = (src, dst)
        rev = (dst, src)

        if link not in self.links and rev not in self.links:
            return

        if link in self.links:
            self.links.remove(link)
        if rev in self.links:
            self.links.remove(rev)

        print("\n❌ Link Removed → Trigger Reconfiguration")

        if self.reconfiguring:
            return

        self.reconfigure_network()

    # -------------------------------
    # 🔥 RECONFIGURATION (FINAL FIX)
    # -------------------------------
    def reconfigure_network(self):
        self.reconfiguring = True

        print("⚠️ Topology change detected → Reconfiguring")
        print("🔄 Clearing flows + forcing relearning")

        for dp in self.dps.values():
            ofproto = dp.ofproto
            parser = dp.ofproto_parser

            # ❌ Delete ALL flows
            mod = parser.OFPFlowMod(
                datapath=dp,
                command=ofproto.OFPFC_DELETE,
                out_port=ofproto.OFPP_ANY,
                out_group=ofproto.OFPG_ANY
            )
            dp.send_msg(mod)

            # ✅ Install temporary FLOOD rule (CRITICAL)
            actions = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]
            inst = [parser.OFPInstructionActions(
                ofproto.OFPIT_APPLY_ACTIONS, actions)]

            mod = parser.OFPFlowMod(
                datapath=dp,
                priority=0,
                match=parser.OFPMatch(),
                instructions=inst
            )
            dp.send_msg(mod)

        self.print_topology("Reconfigured Topology")

        self.reconfiguring = False

    # -------------------------------
    # PRINT TOPOLOGY
    # -------------------------------
    def print_topology(self, msg):
        print("\n========== {} ==========".format(msg))
        print("Switches:", list(self.switches))

        print("Links:")
        if len(self.links) == 0:
            print("  (none)")
        else:
            for l in self.links:
                print("  {} <--> {}".format(l[0], l[1]))

        print("================================\n")
