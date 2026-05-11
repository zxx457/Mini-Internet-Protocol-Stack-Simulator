# Network Devices
# Simple class-based implementation

from config import *
from protocol import *


# ----------------------------
# Helper Functions
# ----------------------------

def print_log(device, layer, msg):
    """Print log message"""
    print(f"{device}: Layer {layer}: {msg}")


# ----------------------------
# Simulator Class
# ----------------------------

class Simulator:
    """
    Network simulator that delivers Ethernet frames.
    Maintains a registry of MAC addresses and their handlers.
    """
    
    def __init__(self):
        """Initialize simulator with empty MAC handler table"""
        self.mac_handlers = {}
    
    def register_mac(self, mac, handler):
        """
        Register a MAC address with its frame handler function.
        
        Args:
            mac: MAC address string (e.g., "AA:BB:CC:DD:EE:FF")
            handler: Function to call when frame arrives for this MAC
        """
        self.mac_handlers[mac.upper()] = handler
    
    def send_frame(self, frame_bytes):
        """
        Send Ethernet frame to destination MAC address.
        Parses destination MAC and calls appropriate handler.
        
        Args:
            frame_bytes: Raw Ethernet frame as bytes
        """
        frame = EthernetFrame.from_bytes(frame_bytes)
        dst = frame.dst_mac.upper()
        handler = self.mac_handlers[dst]
        handler(frame_bytes)


# ----------------------------
# Host Class
# ----------------------------

class Host:
    """
    End host device implementing Layer 2, 3, and 4.
    
    Supports:
    - Layer 4: rdt2.2 reliable data transfer with segmentation
    - Layer 3: IP packet routing
    - Layer 2: Ethernet frame handling
    """
    
    def __init__(self, name, ip, mac, routing_table, arp_table):
        """
        Initialize host with network configuration.
        
        Args:
            name: Host name (e.g., "Host A")
            ip: IP address (e.g., "10.0.1.10")
            mac: MAC address (e.g., "AA:AA:AA:AA:AA:AA")
            routing_table: Tuple of RoutingEntry for routing decisions
            arp_table: Dictionary mapping IP addresses to MAC addresses
        """
        self.name = name
        self.ip = ip
        self.mac = mac.upper()
        self.routing_table = routing_table
        self.arp_table = arp_table
        self.simulator = None
        
        # rdt2.2 state variables
        self.seq = 0              # Current sequence number (0 or 1)
        self.expected = 0         # Expected sequence number (0 or 1)
        self.last_sender = None   # IP of last sender (for ACK reply)
    
    def attach(self, sim):
        """
        Connect host to network simulator.
        
        Args:
            sim: Simulator instance
        """
        self.simulator = sim
        sim.register_mac(self.mac, self.recv_frame)
    
    # ----------------------------
    # Layer 4 - Transport
    # ----------------------------
    
    def send_data(self, dst_ip, data):
        """
        Send data to destination using rdt2.2 protocol.
        Segments data into 500-byte chunks and sends each segment.
        
        Args:
            dst_ip: Destination IP address
            data: Application data as bytes
        """
        print_log(self.name, 4, f"Data received from Application Layer. Data size={len(data)}")
        
        # Segment data into MAX_SEGMENT_DATA byte chunks
        segments = []
        i = 0
        while i < len(data):
            chunk = data[i:i+MAX_SEGMENT_DATA]
            segments.append(chunk)
            i += MAX_SEGMENT_DATA
        
        # Send each segment with rdt2.2
        for seg_data in segments:
            self.send_segment(seg_data, dst_ip)
    
    def send_segment(self, data, dst_ip):
        """
        Send one DATA segment with current sequence number.
        Uses rdt2.2 alternating bit protocol (sequence 0 or 1).
        
        Args:
            data: Segment data (max 500 bytes)
            dst_ip: Destination IP address
        """
        # Create UDP segment with current sequence number
        seg = UDPSegment(
            src_port=DEFAULT_SRC_PORT,
            dst_port=DEFAULT_DST_PORT,
            segment_type=SEGMENT_TYPE_DATA,
            sequence_number=self.seq,
            data=data
        )
        
        print_log(self.name, 4, "Checksum computed")
        print_log(self.name, 4, f"Segment created by adding transport layer header (DATA, seq={self.seq}) (encapsulation)")
        print_log(self.name, 4, "Segment sent to Network Layer")
        
        # Send to Layer 3
        seg_bytes = seg.to_bytes()
        self.send_to_network(seg_bytes, dst_ip)
        
        # Alternate sequence number (0 -> 1, 1 -> 0)
        self.seq = 1 - self.seq
    
    def recv_segment(self, seg_bytes):
        """
        Receive segment from network layer and process.
        Handles both DATA segments (deliver + send ACK) and ACK segments.
        
        Args:
            seg_bytes: UDP segment as bytes
        """
        print_log(self.name, 4, "Segment received from Network Layer")
        print_log(self.name, 4, "Checksum verified")
        
        seg = UDPSegment.from_bytes(seg_bytes)
        
        if seg.segment_type == SEGMENT_TYPE_DATA:
            # Check if sequence number matches expected
            if seg.sequence_number == self.expected:
                # Correct sequence - deliver data to application
                print_log(self.name, 4, f"DATA segment delivered to Application Layer. Data size={len(seg.data)}")
                
                # Create ACK segment with same sequence number
                ack = UDPSegment(
                    src_port=DEFAULT_DST_PORT,
                    dst_port=DEFAULT_SRC_PORT,
                    segment_type=SEGMENT_TYPE_ACK,
                    sequence_number=self.expected,
                    data=b""
                )
                
                print_log(self.name, 4, f"Segment created by adding transport layer header (ACK, seq={self.expected})")
                print_log(self.name, 4, "Segment sent to Network Layer")
                
                # Send ACK back to sender
                ack_bytes = ack.to_bytes()
                self.send_to_network(ack_bytes, self.last_sender)
                
                # Alternate expected sequence number
                self.expected = 1 - self.expected
        
        elif seg.segment_type == SEGMENT_TYPE_ACK:
            # ACK received
            print_log(self.name, 4, f"ACK received: seq={seg.sequence_number}")
    
    # ----------------------------
    # Layer 3 - Network
    # ----------------------------
    
    def send_to_network(self, seg_bytes, dst_ip):
        """
        Create IP packet and forward to data link layer.
        Performs routing table lookup to find next hop.
        
        Args:
            seg_bytes: UDP segment as bytes
            dst_ip: Destination IP address
        """
        # Create IP packet with segment as payload
        pkt = IPPacket(
            src_ip=self.ip,
            dst_ip=dst_ip,
            ttl=DEFAULT_TTL,
            protocol=IP_PROTOCOL_UDP,
            payload=seg_bytes
        )
        
        print_log(self.name, 3, f"Segment received from Transport Layer: SRC_IP={self.ip}, DST_IP={dst_ip}, TTL={DEFAULT_TTL}")
        print_log(self.name, 3, f"Destination IP read: {dst_ip}")
        print_log(self.name, 3, "Routing table lookup performed")
        
        # Lookup next hop in routing table
        entry = longest_prefix_match(dst_ip, self.routing_table)
        next_hop = entry.next_hop_ip if entry.next_hop_ip else dst_ip
        
        print_log(self.name, 3, f"Next-hop IP determined: {next_hop}")
        print_log(self.name, 3, "Outgoing interface selected")
        print_log(self.name, 3, "Packet forwarded to Data Link Layer")
        
        # Forward to Layer 2
        pkt_bytes = pkt.to_bytes()
        self.send_frame_to(pkt_bytes, next_hop)
    
    def recv_packet(self, pkt_bytes):
        """
        Receive IP packet from data link layer.
        Checks if packet is for this host, then delivers to transport layer.
        
        Args:
            pkt_bytes: IP packet as bytes
        """
        pkt = IPPacket.from_bytes(pkt_bytes)
        
        print_log(self.name, 3, f"Packet received from Data Link Layer: SRC_IP={pkt.src_ip}, DST_IP={pkt.dst_ip}, TTL={pkt.ttl}")
        print_log(self.name, 3, f"Destination IP read: {pkt.dst_ip}")
        
        # Check if packet is destined for this host
        if pkt.dst_ip == self.ip:
            print_log(self.name, 3, "Packet identified as local delivery")
            print_log(self.name, 3, "Segment delivered to Transport Layer")
            
            # Store sender IP for ACK reply
            self.last_sender = pkt.src_ip
            
            # Deliver payload to Layer 4
            self.recv_segment(pkt.payload)
    
    # ----------------------------
    # Layer 2 - Data Link
    # ----------------------------
    
    def send_frame_to(self, pkt_bytes, next_hop):
        """
        Create Ethernet frame and send via simulator.
        Uses ARP table to resolve next-hop IP to MAC address.
        
        Args:
            pkt_bytes: IP packet as bytes (frame payload)
            next_hop: Next-hop IP address
        """
        print_log(self.name, 2, "Packet received from Network Layer")
        
        # Resolve next-hop IP to MAC address using ARP table
        dst_mac = self.arp_table.get(next_hop)
        
        print_log(self.name, 2, f"Destination MAC lookup for next-hop IP ({next_hop}) → {dst_mac}")
        
        # Create Ethernet frame with IP packet as payload
        frame = EthernetFrame(
            dst_mac=dst_mac,
            src_mac=self.mac,
            ether_type=ETHERTYPE_IPV4,
            payload=pkt_bytes
        )
        
        print_log(self.name, 2, f"Frame created: SRC_MAC={self.mac}, DST_MAC={dst_mac}")
        print_log(self.name, 2, "Frame sent")
        
        # Send frame via simulator
        if self.simulator:
            self.simulator.send_frame(frame.to_bytes())
    
    def recv_frame(self, frame_bytes):
        """
        Receive Ethernet frame from simulator.
        Learns source MAC address and delivers payload to network layer.
        
        Args:
            frame_bytes: Raw Ethernet frame as bytes
        """
        print_log(self.name, 2, "Frame received")
        
        frame = EthernetFrame.from_bytes(frame_bytes)
        
        # Learn source MAC address
        print_log(self.name, 2, f"Source MAC learned: {frame.src_mac}")
        print_log(self.name, 2, "Packet delivered to Network Layer")
        
        # Extract IP packet and deliver to Layer 3
        self.recv_packet(frame.payload)


# ----------------------------
# Router Class
# ----------------------------

class Router:
    """
    Two-interface router implementing Layer 2 and 3.
    
    Supports:
    - Layer 3: Packet forwarding with TTL decrement and routing
    - Layer 2: Frame forwarding with MAC learning per interface
    """
    
    def __init__(self, name, if1_ip, if1_mac, if2_ip, if2_mac, routing_table):
        """
        Initialize router with two network interfaces.
        
        Args:
            name: Router name (e.g., "Router R1")
            if1_ip: Interface 1 IP address
            if1_mac: Interface 1 MAC address
            if2_ip: Interface 2 IP address
            if2_mac: Interface 2 MAC address
            routing_table: Tuple of RoutingEntry for forwarding decisions
        """
        self.name = name
        self.if1_ip = if1_ip
        self.if1_mac = if1_mac.upper()
        self.if2_ip = if2_ip
        self.if2_mac = if2_mac.upper()
        self.routing_table = routing_table
        self.simulator = None
        
        # MAC learning tables (separate per interface)
        self.mac_if1 = {}  # Interface 1: IP -> MAC mapping
        self.mac_if2 = {}  # Interface 2: IP -> MAC mapping
    
    def attach(self, sim):
        """
        Connect router to network simulator.
        Registers both interface MAC addresses.
        
        Args:
            sim: Simulator instance
        """
        self.simulator = sim
        
        # Register both interfaces with simulator
        sim.register_mac(self.if1_mac, lambda fb: self.recv_on_if1(fb))
        sim.register_mac(self.if2_mac, lambda fb: self.recv_on_if2(fb))
    
    # ----------------------------
    # Layer 2 - Data Link
    # ----------------------------
    
    def recv_on_if1(self, frame_bytes):
        """Receive frame on interface 1 and learn source MAC"""
        print_log(self.name, 2, "Frame received on Interface 1")
        
        frame = EthernetFrame.from_bytes(frame_bytes)
        print_log(self.name, 2, f"Source MAC learned: {frame.src_mac} on Interface 1")
        
        # Learn MAC: extract source IP from packet and map to source MAC
        pkt = IPPacket.from_bytes(frame.payload)
        self.mac_if1[pkt.src_ip] = frame.src_mac
        
        print_log(self.name, 2, "Packet delivered to Network Layer")
        self.forward_packet(frame.payload, "if1")
    
    def recv_on_if2(self, frame_bytes):
        """Receive frame on interface 2 and learn source MAC"""
        print_log(self.name, 2, "Frame received on Interface 2")
        
        frame = EthernetFrame.from_bytes(frame_bytes)
        print_log(self.name, 2, f"Source MAC learned: {frame.src_mac} on Interface 2")
        
        # Learn MAC: extract source IP from packet and map to source MAC
        pkt = IPPacket.from_bytes(frame.payload)
        self.mac_if2[pkt.src_ip] = frame.src_mac
        
        print_log(self.name, 2, "Packet delivered to Network Layer")
        self.forward_packet(frame.payload, "if2")
    
    def send_on_if(self, pkt_bytes, interface, dst_mac):
        """Send frame on specified interface with destination MAC"""
        print_log(self.name, 2, "Packet received from Network Layer")
        print_log(self.name, 2, f"Destination MAC lookup for next-hop IP → {dst_mac}")
        
        # Select source MAC based on outgoing interface
        if interface == "if1":
            src_mac = self.if1_mac
        else:
            src_mac = self.if2_mac
        
        # Create and send frame
        frame = EthernetFrame(
            dst_mac=dst_mac,
            src_mac=src_mac,
            ether_type=ETHERTYPE_IPV4,
            payload=pkt_bytes
        )
        
        print_log(self.name, 2, f"Frame created: SRC_MAC={src_mac}, DST_MAC={dst_mac}")
        print_log(self.name, 2, f"Frame forwarded on Interface {interface[-1]}")
        
        if self.simulator:
            self.simulator.send_frame(frame.to_bytes())
    
    # ----------------------------
    # Layer 3 - Network
    # ----------------------------
    
    def forward_packet(self, pkt_bytes, in_if):
        """
        Forward IP packet after decrementing TTL.
        Performs routing lookup and sends on appropriate interface.
        """
        pkt = IPPacket.from_bytes(pkt_bytes)
        
        print_log(self.name, 3, f"Packet received from Data Link Layer: SRC_IP={pkt.src_ip}, DST_IP={pkt.dst_ip}, TTL={pkt.ttl}")
        print_log(self.name, 3, f"Destination IP read: {pkt.dst_ip}")
        
        # Decrement TTL
        old_ttl = pkt.ttl
        pkt.ttl = pkt.ttl - 1
        print_log(self.name, 3, f"TTL decremented: {old_ttl} → {pkt.ttl}")
        
        # Drop packet if TTL reaches 0
        if pkt.ttl == 0:
            print_log(self.name, 3, "Packet dropped (TTL expired)")
            return
        
        print_log(self.name, 3, "Routing table lookup performed")
        
        # Find route and next hop
        entry = longest_prefix_match(pkt.dst_ip, self.routing_table)
        next_hop = entry.next_hop_ip if entry.next_hop_ip else pkt.dst_ip
        out_if = entry.outgoing_interface
        
        print_log(self.name, 3, f"Next-hop IP determined: {next_hop}")
        print_log(self.name, 3, f"Outgoing interface selected (Interface {out_if[-1]})")
        print_log(self.name, 3, "Packet forwarded to Data Link Layer")
        
        # Lookup MAC address from learned table
        if out_if == "if1":
            dst_mac = self.mac_if1.get(next_hop)
        else:
            dst_mac = self.mac_if2.get(next_hop)
        
        # Send frame on output interface
        new_pkt_bytes = pkt.to_bytes()
        self.send_on_if(new_pkt_bytes, out_if, dst_mac)


# ----------------------------
# Build Topology
# ----------------------------

def build_topology():
    """
    Create network topology with Host A, Router R1, and Host B.
    Initializes all devices and connects them to simulator.
    
    Returns:
        Tuple of (simulator, host_a, router, host_b)
    """
    sim = Simulator()
    
    # Create Host A
    host_a = Host(
        name=HOST_A_NAME,
        ip=HOST_A_IP,
        mac=HOST_A_MAC,
        routing_table=ROUTING_TABLE_HOST_A,
        arp_table=dict(ARP_SEED_HOST_A)
    )
    
    # Create Host B
    host_b = Host(
        name=HOST_B_NAME,
        ip=HOST_B_IP,
        mac=HOST_B_MAC,
        routing_table=ROUTING_TABLE_HOST_B,
        arp_table=dict(ARP_SEED_HOST_B)
    )
    
    # Create Router R1
    router = Router(
        name=ROUTER_NAME,
        if1_ip=R1_IF1_IP,
        if1_mac=R1_IF1_MAC,
        if2_ip=R1_IF2_IP,
        if2_mac=R1_IF2_MAC,
        routing_table=ROUTING_TABLE_R1
    )
    
    # Initialize router MAC tables with host addresses
    router.mac_if1[HOST_A_IP] = HOST_A_MAC
    router.mac_if2[HOST_B_IP] = HOST_B_MAC
    
    # Connect all devices to simulator
    host_a.attach(sim)
    host_b.attach(sim)
    router.attach(sim)
    
    return sim, host_a, router, host_b
