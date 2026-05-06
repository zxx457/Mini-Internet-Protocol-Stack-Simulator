"""
Host, router, and simulation wiring for the protocol stack.

This file is the main integration point: implement encapsulation, decapsulation,
routing, ARP/MAC learning, rdt2.2, and logging in the ``TODO`` sections. The
``Simulator`` class only moves Ethernet frames to the correct MAC handler.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import partial
from typing import Callable, Dict, Optional

from config import (
    ARP_SEED_HOST_A,
    ARP_SEED_HOST_B,
    HOST_A_IP,
    HOST_A_MAC,
    HOST_A_NAME,
    HOST_B_IP,
    HOST_B_MAC,
    HOST_B_NAME,
    R1_IF1_IP,
    R1_IF1_MAC,
    R1_IF2_IP,
    R1_IF2_MAC,
    ROUTER_NAME,
    ROUTING_TABLE_HOST_A,
    ROUTING_TABLE_HOST_B,
    ROUTING_TABLE_R1,
    RoutingEntry,
)
from protocol import EthernetFrame


def emit_log(device_name: str, layer: int, message: str) -> None:
    """
    Print one assignment-style log line.

    Follow the exact wording from the project PDF for full marks (example prefix:
    ``Host A: Layer 4: ...``).
    """
    print(f"{device_name}: Layer {layer}: {message}")


FrameHandler = Callable[[bytes], None]


class Simulator:
    """
    Logical Ethernet segment(s): deliver frames by destination MAC address.

    Register each MAC address that should receive frames. Outbound sends parse
    ``dst_mac`` from the frame and invoke the matching handler.
    """

    def __init__(self) -> None:
        self._by_mac: Dict[str, FrameHandler] = {}

    def register_mac(self, mac: str, handler: FrameHandler) -> None:
        """Associate a MAC address with a callback that receives raw frame bytes."""
        self._by_mac[mac.upper()] = handler

    def send_frame(self, frame_bytes: bytes) -> None:
        """
        Transmit one raw Ethernet frame. Parses destination MAC and dispatches.

        Raises ``KeyError`` if the destination MAC is unknown (extend topology here).
        """
        frame = EthernetFrame.from_bytes(frame_bytes)
        dst = frame.dst_mac.upper()
        handler = self._by_mac[dst]
        handler(frame_bytes)


@dataclass
class Host:
    """
    End host running Layers 2–4 plus a minimal application API.

    Attributes mirror what you need for logging and lookups; extend as required.
    """

    name: str
    ip_address: str
    mac_address: str
    routing_table: tuple[RoutingEntry, ...]
    arp_table: Dict[str, str] = field(default_factory=dict)
    simulator: Optional["Simulator"] = None

    def __post_init__(self) -> None:
        self.mac_address = self.mac_address.upper()

    def attach(self, sim: Simulator) -> None:
        """Register this host's MAC with the simulator."""
        self.simulator = sim
        sim.register_mac(self.mac_address, self.on_ethernet_received)

    # --- L2 -----------------------------------------------------------------

    def on_ethernet_received(self, frame_bytes: bytes) -> None:
        """Entry point when the simulator delivers a frame to this host."""
        # TODO: parse frame, learn source MAC, optionally deliver payload to L3
        raise NotImplementedError("Implement Ethernet receive path")

    def l2_send_frame(self, dst_mac: str, ip_payload: bytes, ether_type: int = 0x0800) -> None:
        """
        Build an Ethernet frame and place it on the simulated wire.

        ``ip_payload`` should be the full Layer 3 packet as raw bytes.
        """
        # TODO: build protocol.EthernetFrame, serialize, call simulator.send_frame
        raise NotImplementedError("Implement Ethernet send path")

    # --- L3 -----------------------------------------------------------------

    def on_packet_from_transport(self, segment_bytes: bytes, dst_ip: str) -> None:
        """L3 receives payload from L4 (UDP-like segment bytes)."""
        raise NotImplementedError("Implement IP encapsulation and forwarding")

    def on_packet_from_layer2(self, ip_packet_bytes: bytes) -> None:
        """Decode IP-like packet from Ethernet payload."""
        raise NotImplementedError("Implement IP receive and TTL/local delivery rules")

    # --- L4 -----------------------------------------------------------------

    def send_application_data(self, dst_ip: str, payload: bytes) -> None:
        """
        Send ``payload`` to ``dst_ip`` using rdt2.2 and optional segmentation.

        For messages longer than ``config.MAX_SEGMENT_DATA``, split into
        multiple segments and run stop-and-wait for each in order.
        """
        raise NotImplementedError("Implement rdt2.2 sender and segmentation")

    def on_segment_from_network(self, segment_bytes: bytes) -> None:
        """L4 entry for a payload coming from L3 (may be DATA or ACK)."""
        raise NotImplementedError("Implement rdt2.2 receiver and checksum handling")


@dataclass
class Router:
    """
    Two-interface router: separate MAC and IP processing per interface.

    Use ``interfaces`` to map a logical name (``if1``, ``if2``) to IP and MAC.
    """

    name: str
    interfaces: Dict[str, tuple[str, str]]  # if_name -> (ip, mac)
    routing_table: tuple[RoutingEntry, ...]
    arp_per_interface: Dict[str, Dict[str, str]] = field(default_factory=dict)
    simulator: Optional[Simulator] = None

    def __post_init__(self) -> None:
        for k in self.arp_per_interface:
            self.arp_per_interface[k] = dict(self.arp_per_interface[k])

    def attach(self, sim: Simulator) -> None:
        """Register each interface MAC so inbound frames reach ``on_ethernet_received``."""
        self.simulator = sim
        for if_name, (_, mac) in self.interfaces.items():
            mac_u = mac.upper()
            sim.register_mac(mac_u, partial(self.on_ethernet_received, if_name))

    def on_ethernet_received(self, interface_name: str, frame_bytes: bytes) -> None:
        """Layer 2 entry for frames arriving on ``interface_name``."""
        raise NotImplementedError("Implement learning + deliver IP payload to L3")

    def forward_ip_packet(self, inbound_iface: str, packet_bytes: bytes) -> None:
        """Layer 3 forwarding decision after optional TTL decrement."""
        raise NotImplementedError("Implement routing, TTL, and L2 rewrite per interface")


def build_topology() -> tuple[Simulator, Host, Router, Host]:
    """
    Construct the fixed three-node topology from the assignment brief.

    Returns:
        ``(simulator, host_a, router_r1, host_b)`` — extend ``ARP`` seeding as needed.
    """
    sim = Simulator()

    host_a = Host(
        name=HOST_A_NAME,
        ip_address=HOST_A_IP,
        mac_address=HOST_A_MAC,
        routing_table=ROUTING_TABLE_HOST_A,
        arp_table=dict(ARP_SEED_HOST_A),
    )

    host_b = Host(
        name=HOST_B_NAME,
        ip_address=HOST_B_IP,
        mac_address=HOST_B_MAC,
        routing_table=ROUTING_TABLE_HOST_B,
        arp_table=dict(ARP_SEED_HOST_B),
    )

    router = Router(
        name=ROUTER_NAME,
        interfaces={
            "if1": (R1_IF1_IP, R1_IF1_MAC),
            "if2": (R1_IF2_IP, R1_IF2_MAC),
        },
        routing_table=ROUTING_TABLE_R1,
        arp_per_interface={"if1": {}, "if2": {}},
    )

    host_a.attach(sim)
    host_b.attach(sim)
    router.attach(sim)

    return sim, host_a, router, host_b
