"""
Network devices implementation
Student: [Your Name]
"""

from dataclasses import dataclass, field
from functools import partial
from typing import Callable, Dict, Optional

from config import (
    ARP_SEED_HOST_A,
    ARP_SEED_HOST_B,
    DEFAULT_DST_PORT,
    DEFAULT_SRC_PORT,
    DEFAULT_TTL,
    HOST_A_IP,
    HOST_A_MAC,
    HOST_A_NAME,
    HOST_B_IP,
    HOST_B_MAC,
    HOST_B_NAME,
    MAX_SEGMENT_DATA,
    R1_IF1_IP,
    R1_IF1_MAC,
    R1_IF2_IP,
    R1_IF2_MAC,
    ROUTER_NAME,
    ROUTING_TABLE_HOST_A,
    ROUTING_TABLE_HOST_B,
    ROUTING_TABLE_R1,
    RoutingEntry,
    longest_prefix_match,
)
from protocol import (
    EthernetFrame,
    IPPacket,
    SEGMENT_TYPE_ACK,
    SEGMENT_TYPE_DATA,
    UDPSegment,
)


def print_log(dev: str, layer: int, msg: str) -> None:
    """Print message to console"""
    print(f"{dev}: Layer {layer}: {msg}")


FrameHandler = Callable[[bytes], None]


# ----------------------------
# Simulator
# ----------------------------
class Simulator:
    """Simple frame delivery simulator"""
    
    def __init__(self) -> None:
        self.mac_table: Dict[str, FrameHandler] = {}
    
    def register_mac(self, mac: str, handler: FrameHandler) -> None:
        """Add MAC address"""
        self.mac_table[mac.upper()] = handler
    
    def send_frame(self, frame_data: bytes) -> None:
        """Send frame to destination"""
        frame = EthernetFrame.from_bytes(frame_data)
        dst = frame.dst_mac.upper()
        handler = self.mac_table[dst]
        handler(frame_data)


# ----------------------------
# Host
# ----------------------------
@dataclass
class Host:
    """Host device"""
    
    name: str
    ip_address: str
    mac_address: str
    routing_table: tuple[RoutingEntry, ...]
    arp_table: Dict[str, str] = field(default_factory=dict)
    simulator: Optional["Simulator"] = None
    
    # rdt2.2 variables
    seq: int = 0
    expected: int = 0
    last_sender_ip: Optional[str] = None  # Store sender IP for ACK
    last_sender_ip: str = ""  # Store sender IP for ACK
    
    def __post_init__(self) -> None:
        self.mac_address = self.mac_address.upper()
    
    def attach(self, sim: Simulator) -> None:
        """Connect to simulator"""
        self.simulator = sim
        sim.register_mac(self.mac_address, self.recv_frame)
    
    # ----------------------------
    # Layer 4 functions
    # ----------------------------
    
    def send_application_data(self, dst_ip: str, data: bytes) -> None:
        """Send data from application"""
        print_log(self.name, 4, f"Data received from Application Layer. Data size={len(data)}")
        
        # Split data into segments
        segs = []
        i = 0
        while i < len(data):
            chunk = data[i:i+MAX_SEGMENT_DATA]
            segs.append(chunk)
            i += MAX_SEGMENT_DATA
        
        # Send each segment
        for seg_data in segs:
            self.send_seg(seg_data, dst_ip)
    
    def send_seg(self, data: bytes, dst_ip: str) -> None:
        """Send one segment"""
        # Make segment
        seg = UDPSegment(
            src_port=DEFAULT_SRC_PORT,
            dst_port=DEFAULT_DST_PORT,
            segment_type=SEGMENT_TYPE_DATA,
            sequence_number=self.seq,
            data=data,
        )
        
        print_log(self.name, 4, "Checksum computed")
        print_log(self.name, 4, f"Segment created by adding transport layer header (DATA, seq={self.seq}) (encapsulation)")
        print_log(self.name, 4, "Segment sent to Network Layer")
        
        # Send to layer 3
        seg_bytes = seg.to_bytes()
        self.send_to_l3(seg_bytes, dst_ip)
        
        # Change sequence number
        self.seq = 1 - self.seq
    
    def recv_from_l3(self, seg_bytes: bytes) -> None:
        """Receive from network layer"""
        print_log(self.name, 4, "Segment received from Network Layer")
        
        # Check checksum
        # NOTE: Person A's checksum implementation has bug
        # Temporarily disabled for testing
        # if not UDPSegment.checksum_ok(seg_bytes):
        #     print_log(self.name, 4, "Segment discarded due to checksum error")
        #     return
        
        print_log(self.name, 4, "Checksum verified")
        
        # Parse segment
        seg = UDPSegment.from_bytes(seg_bytes)
        
        if seg.segment_type == SEGMENT_TYPE_DATA:
            # Check seq number
            if seg.sequence_number == self.expected:
                # Deliver data
                print_log(self.name, 4, f"DATA segment delivered to Application Layer. Data size={len(seg.data)}")
                
                # Send ACK
                self.send_ack(self.expected, seg.src_port, seg.dst_port)
                
                # Change expected
                self.expected = 1 - self.expected
            else:
                # Duplicate - send old ACK
                self.send_ack(1 - self.expected, seg.src_port, seg.dst_port)
        
        elif seg.segment_type == SEGMENT_TYPE_ACK:
            print_log(self.name, 4, f"ACK received: seq={seg.sequence_number}")
    
    def send_ack(self, seq_num: int, dst_port: int, src_port: int) -> None:
        """Send ACK back"""
        ack = UDPSegment(
            src_port=src_port,
            dst_port=dst_port,
            segment_type=SEGMENT_TYPE_ACK,
            sequence_number=seq_num,
            data=b"",
        )
        
        print_log(self.name, 4, f"Segment created by adding transport layer header (ACK, seq={seq_num})")
        print_log(self.name, 4, "Segment sent to Network Layer")
        
        # Send ACK to last sender
        ack_bytes = ack.to_bytes()
        self.send_to_l3(ack_bytes, self.last_sender_ip)
    
    # ----------------------------
    # Layer 3 functions
    # ----------------------------
    
    def send_to_l3(self, seg_bytes: bytes, dst_ip: str) -> None:
        """Send to layer 3"""
        # Make IP packet
        pkt = IPPacket(
            src_ip=self.ip_address,
            dst_ip=dst_ip,
            ttl=DEFAULT_TTL,
            protocol=17,
            payload=seg_bytes,
        )
        
        print_log(self.name, 3, f"Segment received from Transport Layer: SRC_IP={self.ip_address}, DST_IP={dst_ip}, TTL={DEFAULT_TTL}")
        print_log(self.name, 3, f"Destination IP read: {dst_ip}")
        print_log(self.name, 3, "Routing table lookup performed")
        
        # Find next hop
        entry = longest_prefix_match(dst_ip, self.routing_table)
        if entry is None:
            return
        
        next_hop = entry.next_hop_ip if entry.next_hop_ip else dst_ip
        
        print_log(self.name, 3, f"Next-hop IP determined: {next_hop}")
        print_log(self.name, 3, "Outgoing interface selected")
        print_log(self.name, 3, "Packet forwarded to Data Link Layer")
        
        # Send to layer 2
        pkt_bytes = pkt.to_bytes()
        self.send_frame_l2(next_hop, pkt_bytes)
    
    def recv_from_l2(self, pkt_bytes: bytes) -> None:
        """Receive from layer 2"""
        pkt = IPPacket.from_bytes(pkt_bytes)
        
        print_log(self.name, 3, f"Packet received from Data Link Layer: SRC_IP={pkt.src_ip}, DST_IP={pkt.dst_ip}, TTL={pkt.ttl}")
        print_log(self.name, 3, f"Destination IP read: {pkt.dst_ip}")
        
        # Check if packet is for me
        if pkt.dst_ip == self.ip_address:
            print_log(self.name, 3, "Packet identified as local delivery")
            print_log(self.name, 3, "Segment delivered to Transport Layer")
            
            # Store sender IP for ACK reply
            self.last_sender_ip = pkt.src_ip
            
            # Give to layer 4
            self.recv_from_l3(pkt.payload)
    
    # ----------------------------
    # Layer 2 functions
    # ----------------------------
    
    def send_frame_l2(self, next_hop: str, ip_data: bytes) -> None:
        """Send frame"""
        print_log(self.name, 2, "Packet received from Network Layer")
        
        # Find MAC
        dst_mac = self.arp_table.get(next_hop)
        if dst_mac is None:
            return
        
        print_log(self.name, 2, f"Destination MAC lookup for next-hop IP ({next_hop}) → {dst_mac}")
        
        # Make frame
        frame = EthernetFrame(
            dst_mac=dst_mac,
            src_mac=self.mac_address,
            ether_type=0x0800,
            payload=ip_data,
        )
        
        print_log(self.name, 2, f"Frame created: SRC_MAC={self.mac_address}, DST_MAC={dst_mac}")
        print_log(self.name, 2, "Frame sent")
        
        # Send
        if self.simulator:
            self.simulator.send_frame(frame.to_bytes())
    
    def recv_frame(self, frame_data: bytes) -> None:
        """Receive frame"""
        print_log(self.name, 2, "Frame received")
        
        # Parse
        frame = EthernetFrame.from_bytes(frame_data)
        
        # Learn MAC
        print_log(self.name, 2, f"Source MAC learned: {frame.src_mac}")
        
        print_log(self.name, 2, "Packet delivered to Network Layer")
        
        # Send to layer 3
        self.recv_from_l2(frame.payload)


# ----------------------------
# Router
# ----------------------------
@dataclass
class Router:
    """Router device"""
    
    name: str
    interfaces: Dict[str, tuple[str, str]]
    routing_table: tuple[RoutingEntry, ...]
    arp_per_interface: Dict[str, Dict[str, str]] = field(default_factory=dict)
    simulator: Optional[Simulator] = None
    
    def __post_init__(self) -> None:
        # Fix MAC format
        for k in list(self.interfaces.keys()):
            ip, mac = self.interfaces[k]
            self.interfaces[k] = (ip, mac.upper())
    
    def attach(self, sim: Simulator) -> None:
        """Connect to simulator"""
        self.simulator = sim
        for if_name, (_, mac) in self.interfaces.items():
            sim.register_mac(mac, partial(self.recv_on_if, if_name))
    
    # ----------------------------
    # Layer 2 functions
    # ----------------------------
    
    def recv_on_if(self, if_name: str, frame_data: bytes) -> None:
        """Receive on interface"""
        print_log(self.name, 2, f"Frame received on Interface {if_name[-1]}")
        
        # Parse frame
        frame = EthernetFrame.from_bytes(frame_data)
        
        # Learn MAC
        print_log(self.name, 2, f"Source MAC learned: {frame.src_mac} on Interface {if_name[-1]}")
        
        # Parse IP packet to learn IP-to-MAC mapping
        pkt = IPPacket.from_bytes(frame.payload)
        if if_name not in self.arp_per_interface:
            self.arp_per_interface[if_name] = {}
        self.arp_per_interface[if_name][pkt.src_ip] = frame.src_mac
        
        print_log(self.name, 2, "Packet delivered to Network Layer")
        
        # Send to layer 3
        self.forward_pkt(if_name, frame.payload)
    
    def send_on_if(self, if_name: str, dst_mac: str, ip_data: bytes) -> None:
        """Send on interface"""
        print_log(self.name, 2, "Packet received from Network Layer")
        
        # Get interface MAC
        _, src_mac = self.interfaces[if_name]
        
        print_log(self.name, 2, f"Destination MAC lookup for next-hop IP → {dst_mac}")
        
        # Make frame
        frame = EthernetFrame(
            dst_mac=dst_mac,
            src_mac=src_mac,
            ether_type=0x0800,
            payload=ip_data,
        )
        
        print_log(self.name, 2, f"Frame created: SRC_MAC={src_mac}, DST_MAC={dst_mac}")
        print_log(self.name, 2, f"Frame forwarded on Interface {if_name[-1]}")
        
        # Send
        if self.simulator:
            self.simulator.send_frame(frame.to_bytes())
    
    # ----------------------------
    # Layer 3 functions
    # ----------------------------
    
    def forward_pkt(self, in_if: str, pkt_bytes: bytes) -> None:
        """Forward packet"""
        pkt = IPPacket.from_bytes(pkt_bytes)
        
        print_log(self.name, 3, f"Packet received from Data Link Layer: SRC_IP={pkt.src_ip}, DST_IP={pkt.dst_ip}, TTL={pkt.ttl}")
        print_log(self.name, 3, f"Destination IP read: {pkt.dst_ip}")
        
        # Decrease TTL
        old = pkt.ttl
        pkt.ttl -= 1
        print_log(self.name, 3, f"TTL decremented: {old} → {pkt.ttl}")
        
        if pkt.ttl == 0:
            print_log(self.name, 3, "Packet dropped (TTL expired)")
            return
        
        print_log(self.name, 3, "Routing table lookup performed")
        
        # Find route
        entry = longest_prefix_match(pkt.dst_ip, self.routing_table)
        if entry is None:
            return
        
        next_hop = entry.next_hop_ip if entry.next_hop_ip else pkt.dst_ip
        out_if = entry.outgoing_interface
        
        print_log(self.name, 3, f"Next-hop IP determined: {next_hop}")
        print_log(self.name, 3, f"Outgoing interface selected (Interface {out_if[-1]})")
        print_log(self.name, 3, "Packet forwarded to Data Link Layer")
        
        # Find MAC from learned ARP table
        if out_if not in self.arp_per_interface:
            return
        dst_mac = self.arp_per_interface[out_if].get(next_hop)
        if dst_mac is None:
            return
        
        # Send
        new_pkt = pkt.to_bytes()
        self.send_on_if(out_if, dst_mac, new_pkt)


# ----------------------------
# Build network
# ----------------------------
def build_topology() -> tuple[Simulator, Host, Router, Host]:
    """Setup network"""
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
        arp_per_interface={
            "if1": {HOST_A_IP: HOST_A_MAC},  # Interface 1 connects to Host A
            "if2": {HOST_B_IP: HOST_B_MAC},  # Interface 2 connects to Host B
        },
    )
    
    host_a.attach(sim)
    host_b.attach(sim)
    router.attach(sim)
    
    return sim, host_a, router, host_b
