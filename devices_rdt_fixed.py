# Network Devices Implementation
# CITS3002 Project - Protocol Stack

from config import *
from protocol import *
import time


def print_log(dev_name, layer_num, message):
    """Print the log for testing"""
    print(f"{dev_name}: Layer {layer_num}: {message}")
    time.sleep(0.2)


# ----------------------------
# Simulator Class
# ----------------------------

class Simulator:
    """
    This class is for simulate the network.
    It can send frame to correct MAC address.
    """
    
    def __init__(self):
        # Dictionary to store MAC and handler
        self.mac_handlers = {}
    
    def register_mac(self, mac_addr, handler_func):
        """Register the MAC address with handler function"""
        self.mac_handlers[mac_addr.upper()] = handler_func
    
    def send_frame(self, frame_data):
        """
        Send frame to destination MAC.
        Parse the frame and find handler, then call it.
        """
        frame = EthernetFrame.from_bytes(frame_data)
        dest_mac = frame.dst_mac.upper()
        handler = self.mac_handlers[dest_mac]
        handler(frame_data)


# ----------------------------
# Host Class
# ----------------------------

class Host:
    """
    Host class implement Layer 2, 3, 4.
    It can send and receive data using protocol stack.
    """
    
    def __init__(self, host_name, ip_addr, mac_addr, route_table, arp_map):
        # Basic information
        self.name = host_name
        self.ip = ip_addr
        self.mac = mac_addr.upper()
        self.route_table = route_table
        self.arp_map = arp_map
        self.sim = None
        
        # For rdt2.2 protocol
        self.current_seq = 0          # Current DATA sequence number to send
        self.expect_seq = 0           # Expected DATA sequence number to receive
        self.sender_ip = None         # Store sender IP for ACK reply

        # Sender-side rdt2.2 state
        self.waiting_for_ack = False
        self.ack_received = False
        self.pending_ack_seq = None
        self.pending_segment_bytes = None
        self.pending_dest_ip = None
        self.max_retransmissions = 3

        # Receiver-side rdt2.2 state
        self.last_ack_seq = None
    
    def attach(self, simulator):
        """Connect this host to simulator"""
        self.sim = simulator
        simulator.register_mac(self.mac, self.recv_frame)
    
    # ----------------------------
    # Layer 4 Functions
    # ----------------------------
    
    def send_data(self, dest_ip, app_data):
        """
        This function send data from application layer.
        It will split data into segments if data is big.
        """
        print_log(self.name, 4, f"Data received from Application Layer. Data size={len(app_data)}")
        
        # Make segments list
        seg_list = []
        pos = 0
        while pos < len(app_data):
            piece = app_data[pos:pos+MAX_SEGMENT_DATA]
            seg_list.append(piece)
            pos += MAX_SEGMENT_DATA
        
        # Send all segments one by one
        for seg_data in seg_list:
            self.send_one_segment(seg_data, dest_ip)
    
    def send_one_segment(self, seg_data, dest_ip):
        """
        Send one DATA segment using rdt2.2.
        The sender waits for the correct ACK before moving to the next sequence number.
        If an incorrect/duplicate ACK is received, the same DATA segment is retransmitted.
        """
        seq = self.current_seq

        # Make the DATA segment once and keep it as the pending segment
        segment = UDPSegment(
            src_port=DEFAULT_SRC_PORT,
            dst_port=DEFAULT_DST_PORT,
            segment_type=SEGMENT_TYPE_DATA,
            sequence_number=seq,
            data=seg_data
        )
        seg_bytes = segment.to_bytes()

        self.pending_ack_seq = seq
        self.pending_segment_bytes = seg_bytes
        self.pending_dest_ip = dest_ip
        self.waiting_for_ack = True
        self.ack_received = False

        attempts = 0
        while self.waiting_for_ack and attempts <= self.max_retransmissions:
            if attempts == 0:
                print_log(self.name, 4, "Checksum computed")
                print_log(self.name, 4, f"Segment created by adding transport layer header (DATA, seq={seq}) (encapsulation)")
                print_log(self.name, 4, "Segment sent to Network Layer")
            else:
                print_log(self.name, 4, f"Segment retransmitted due to incorrect ACK (DATA, seq={seq})")
                print_log(self.name, 4, "Segment sent to Network Layer")

            # In this simulator, send_to_net_layer() is synchronous: the ACK is received
            # before this call returns if the packet successfully reaches the receiver.
            self.send_to_net_layer(seg_bytes, dest_ip)
            attempts += 1

            if self.ack_received:
                break

        if self.ack_received:
            # Only now is it safe to alternate the sequence number
            self.current_seq = 1 - self.current_seq
        else:
            print_log(self.name, 4, f"Transmission failed after {self.max_retransmissions} retransmissions")

        # Clear sender-side pending state
        self.waiting_for_ack = False
        self.pending_ack_seq = None
        self.pending_segment_bytes = None
        self.pending_dest_ip = None
        self.ack_received = False
    
    def recv_from_net_layer(self, seg_bytes):
        """
        Receive segment from network layer.
        Check the type and process it.
        """
        print_log(self.name, 4, "Segment received from Network Layer")
        print_log(self.name, 4, "Checksum verified")
        
        # Parse the segment
        segment = UDPSegment.from_bytes(seg_bytes)
        
        if segment.segment_type == SEGMENT_TYPE_DATA:
            # This is DATA segment
            if segment.sequence_number == self.expect_seq:
                # Correct sequence: deliver data and ACK this sequence
                print_log(self.name, 4, f"DATA segment delivered to Application Layer. Data size={len(segment.data)}")
                self.send_ack(self.expect_seq)
                self.last_ack_seq = self.expect_seq
                self.expect_seq = 1 - self.expect_seq
            else:
                # Duplicate DATA segment: do not deliver again; resend last ACK
                print_log(self.name, 4, f"Duplicate DATA segment received: seq={segment.sequence_number}")
                if self.last_ack_seq is not None:
                    print_log(self.name, 4, f"Re-sending last ACK: seq={self.last_ack_seq}")
                    self.send_ack(self.last_ack_seq)
        
        elif segment.segment_type == SEGMENT_TYPE_ACK:
            print_log(self.name, 4, f"ACK received: seq={segment.sequence_number}")

            # Sender side: correct ACK means the pending DATA segment is complete
            if self.waiting_for_ack and segment.sequence_number == self.pending_ack_seq:
                self.ack_received = True
                self.waiting_for_ack = False
            elif self.waiting_for_ack:
                # Wrong/duplicate ACK: keep waiting; send_one_segment() will retransmit
                print_log(self.name, 4, f"Incorrect or duplicate ACK received: expected seq={self.pending_ack_seq}, got seq={segment.sequence_number}")
    
    def send_ack(self, ack_seq):
        """Create and send an ACK segment with the given sequence number."""
        ack_segment = UDPSegment(
            src_port=DEFAULT_DST_PORT,
            dst_port=DEFAULT_SRC_PORT,
            segment_type=SEGMENT_TYPE_ACK,
            sequence_number=ack_seq,
            data=b""
        )

        print_log(self.name, 4, f"Segment created by adding transport layer header (ACK, seq={ack_seq})")
        print_log(self.name, 4, f"ACK sent: seq={ack_seq}")
        print_log(self.name, 4, "Segment sent to Network Layer")

        ack_bytes = ack_segment.to_bytes()
        self.send_to_net_layer(ack_bytes, self.sender_ip)

    # ----------------------------
    # Layer 3 Functions
    # ----------------------------
    
    def send_to_net_layer(self, segment_bytes, dest_ip):
        """
        Send segment to network layer.
        Make IP packet and do routing.
        """
        # Create IP packet with segment inside
        ip_packet = IPPacket(
            src_ip=self.ip,
            dst_ip=dest_ip,
            ttl=DEFAULT_TTL,
            protocol=IP_PROTOCOL_UDP,
            payload=segment_bytes
        )
        
        print_log(self.name, 3, f"Segment received from Transport Layer: SRC_IP={self.ip}, DST_IP={dest_ip}, TTL={DEFAULT_TTL}")
        print_log(self.name, 3, f"Destination IP read: {dest_ip}")
        print_log(self.name, 3, "Routing table lookup performed")
        
        # Find next hop IP from routing table
        route_entry = longest_prefix_match(dest_ip, self.route_table)
        next_ip = route_entry.next_hop_ip if route_entry.next_hop_ip else dest_ip
        
        print_log(self.name, 3, f"Next-hop IP determined: {next_ip}")
        print_log(self.name, 3, "Outgoing interface selected")
        print_log(self.name, 3, "Packet forwarded to Data Link Layer")
        
        # Send to data link layer
        packet_bytes = ip_packet.to_bytes()
        self.send_frame_out(packet_bytes, next_ip)
    
    def recv_from_link_layer(self, packet_bytes):
        """
        Receive IP packet from data link layer.
        Check if it's for this host.
        """
        ip_packet = IPPacket.from_bytes(packet_bytes)
        
        print_log(self.name, 3, f"Packet received from Data Link Layer: SRC_IP={ip_packet.src_ip}, DST_IP={ip_packet.dst_ip}, TTL={ip_packet.ttl}")
        print_log(self.name, 3, f"Destination IP read: {ip_packet.dst_ip}")
        
        # Check destination IP
        if ip_packet.dst_ip == self.ip:
            # This packet is for me
            print_log(self.name, 3, "Packet identified as local delivery")
            print_log(self.name, 3, "Segment delivered to Transport Layer")
            
            # Remember sender IP for ACK reply
            self.sender_ip = ip_packet.src_ip
            
            # Give payload to transport layer
            self.recv_from_net_layer(ip_packet.payload)
    
    # ----------------------------
    # Layer 2 Functions
    # ----------------------------
    
    def send_frame_out(self, packet_bytes, next_hop_ip):
        """
        Make ethernet frame and send out.
        Need to find MAC address for next hop.
        """
        print_log(self.name, 2, "Packet received from Network Layer")
        
        # Look up MAC address in ARP table
        dest_mac = self.arp_map.get(next_hop_ip)
        
        print_log(self.name, 2, f"Destination MAC lookup for next-hop IP ({next_hop_ip}) → {dest_mac}")
        
        # Make ethernet frame
        eth_frame = EthernetFrame(
            dst_mac=dest_mac,
            src_mac=self.mac,
            ether_type=ETHERTYPE_IPV4,
            payload=packet_bytes
        )
        
        print_log(self.name, 2, f"Frame created: SRC_MAC={self.mac}, DST_MAC={dest_mac}")
        print_log(self.name, 2, "Frame sent")
        
        # Send through simulator
        if self.sim:
            self.sim.send_frame(eth_frame.to_bytes())
    
    def recv_frame(self, frame_bytes):
        """
        Receive ethernet frame.
        Learn MAC address and pass to network layer.
        """
        print_log(self.name, 2, "Frame received")
        
        # Parse the frame
        eth_frame = EthernetFrame.from_bytes(frame_bytes)
        
        # Learn the source MAC
        print_log(self.name, 2, f"Source MAC learned: {eth_frame.src_mac}")
        print_log(self.name, 2, "Packet delivered to Network Layer")
        
        # Give packet to network layer
        self.recv_from_link_layer(eth_frame.payload)


# ----------------------------
# Router Class
# ----------------------------

class Router:
    """
    Router class with two interface.
    Can forward packet between two network.
    """
    
    def __init__(self, router_name, if1_ip_addr, if1_mac_addr, if2_ip_addr, if2_mac_addr, route_table):
        # Basic information
        self.name = router_name
        self.if1_ip = if1_ip_addr
        self.if1_mac = if1_mac_addr.upper()
        self.if2_ip = if2_ip_addr
        self.if2_mac = if2_mac_addr.upper()
        self.route_table = route_table
        self.sim = None
        
        # MAC learning table for each interface
        self.mac_table_if1 = {}
        self.mac_table_if2 = {}
    
    def attach(self, simulator):
        """Connect router to simulator"""
        self.sim = simulator
        
        # Register two interface MAC address
        simulator.register_mac(self.if1_mac, self.recv_if1_wrapper)
        simulator.register_mac(self.if2_mac, self.recv_if2_wrapper)
    
    # Wrapper function for interface 1
    def recv_if1_wrapper(self, frame_bytes):
        """This function receive frame on interface 1"""
        self.recv_on_interface("if1", frame_bytes)
    
    # Wrapper function for interface 2
    def recv_if2_wrapper(self, frame_bytes):
        """This function receive frame on interface 2"""
        self.recv_on_interface("if2", frame_bytes)
    
    # ----------------------------
    # Layer 2 Functions
    # ----------------------------
    
    def recv_on_interface(self, if_name, frame_bytes):
        """
        Receive frame on interface.
        Learn MAC address and forward to network layer.
        """
        interface_num = if_name[-1]
        print_log(self.name, 2, f"Frame received on Interface {interface_num}")
        
        # Parse frame
        eth_frame = EthernetFrame.from_bytes(frame_bytes)
        print_log(self.name, 2, f"Source MAC learned: {eth_frame.src_mac} on Interface {interface_num}")
        
        # Learn MAC address from packet
        ip_packet = IPPacket.from_bytes(eth_frame.payload)
        if if_name == "if1":
            self.mac_table_if1[ip_packet.src_ip] = eth_frame.src_mac
        else:
            self.mac_table_if2[ip_packet.src_ip] = eth_frame.src_mac
        
        print_log(self.name, 2, "Packet delivered to Network Layer")
        
        # Give packet to network layer
        self.do_forwarding(eth_frame.payload)
    
    def send_on_interface(self, packet_bytes, if_name, dest_mac_addr):
        """
        Send frame on interface.
        Make frame and send out through interface.
        """
        print_log(self.name, 2, "Packet received from Network Layer")
        print_log(self.name, 2, f"Destination MAC lookup for next-hop IP → {dest_mac_addr}")
        
        # Choose source MAC base on interface
        if if_name == "if1":
            source_mac = self.if1_mac
        else:
            source_mac = self.if2_mac
        
        # Make frame
        eth_frame = EthernetFrame(
            dst_mac=dest_mac_addr,
            src_mac=source_mac,
            ether_type=ETHERTYPE_IPV4,
            payload=packet_bytes
        )
        
        interface_num = if_name[-1]
        print_log(self.name, 2, f"Frame created: SRC_MAC={source_mac}, DST_MAC={dest_mac_addr}")
        print_log(self.name, 2, f"Frame forwarded on Interface {interface_num}")
        
        # Send through simulator
        if self.sim:
            self.sim.send_frame(eth_frame.to_bytes())
    
    def send_ack(self, ack_seq):
        """Create and send an ACK segment with the given sequence number."""
        ack_segment = UDPSegment(
            src_port=DEFAULT_DST_PORT,
            dst_port=DEFAULT_SRC_PORT,
            segment_type=SEGMENT_TYPE_ACK,
            sequence_number=ack_seq,
            data=b""
        )

        print_log(self.name, 4, f"Segment created by adding transport layer header (ACK, seq={ack_seq})")
        print_log(self.name, 4, f"ACK sent: seq={ack_seq}")
        print_log(self.name, 4, "Segment sent to Network Layer")

        ack_bytes = ack_segment.to_bytes()
        self.send_to_net_layer(ack_bytes, self.sender_ip)

    # ----------------------------
    # Layer 3 Functions
    # ----------------------------
    
    def do_forwarding(self, packet_bytes):
        """
        Forward packet to destination.
        Decrease TTL and check routing table.
        """
        ip_packet = IPPacket.from_bytes(packet_bytes)
        
        print_log(self.name, 3, f"Packet received from Data Link Layer: SRC_IP={ip_packet.src_ip}, DST_IP={ip_packet.dst_ip}, TTL={ip_packet.ttl}")
        print_log(self.name, 3, f"Destination IP read: {ip_packet.dst_ip}")
        
        # Decrease TTL by 1
        old_ttl_value = ip_packet.ttl
        ip_packet.ttl = ip_packet.ttl - 1
        print_log(self.name, 3, f"TTL decremented: {old_ttl_value} → {ip_packet.ttl}")
        
        # Check if TTL become 0
        if ip_packet.ttl == 0:
            print_log(self.name, 3, "Packet dropped (TTL expired)")
            return
        
        print_log(self.name, 3, "Routing table lookup performed")
        
        # Find route from routing table
        route_entry = longest_prefix_match(ip_packet.dst_ip, self.route_table)
        next_hop_ip = route_entry.next_hop_ip if route_entry.next_hop_ip else ip_packet.dst_ip
        out_interface = route_entry.outgoing_interface
        
        interface_num = out_interface[-1]
        print_log(self.name, 3, f"Next-hop IP determined: {next_hop_ip}")
        print_log(self.name, 3, f"Outgoing interface selected (Interface {interface_num})")
        print_log(self.name, 3, "Packet forwarded to Data Link Layer")
        
        # Find MAC address from learning table
        if out_interface == "if1":
            dest_mac_addr = self.mac_table_if1.get(next_hop_ip)
        else:
            dest_mac_addr = self.mac_table_if2.get(next_hop_ip)
        
        # Send frame out
        new_packet_bytes = ip_packet.to_bytes()
        self.send_on_interface(new_packet_bytes, out_interface, dest_mac_addr)


# ----------------------------
# Build Topology Function
# ----------------------------

def build_topology():
    """
    Build the network topology.
    Create simulator, hosts and router, connect them together.
    """
    # Create simulator
    sim = Simulator()
    
    # Create Host A
    host_a = Host(
        host_name=HOST_A_NAME,
        ip_addr=HOST_A_IP,
        mac_addr=HOST_A_MAC,
        route_table=ROUTING_TABLE_HOST_A,
        arp_map=dict(ARP_SEED_HOST_A)
    )
    
    # Create Host B
    host_b = Host(
        host_name=HOST_B_NAME,
        ip_addr=HOST_B_IP,
        mac_addr=HOST_B_MAC,
        route_table=ROUTING_TABLE_HOST_B,
        arp_map=dict(ARP_SEED_HOST_B)
    )
    
    # Create Router R1
    router_r1 = Router(
        router_name=ROUTER_NAME,
        if1_ip_addr=R1_IF1_IP,
        if1_mac_addr=R1_IF1_MAC,
        if2_ip_addr=R1_IF2_IP,
        if2_mac_addr=R1_IF2_MAC,
        route_table=ROUTING_TABLE_R1
    )
    
    # Put host MAC address in router table at beginning
    router_r1.mac_table_if1[HOST_A_IP] = HOST_A_MAC
    router_r1.mac_table_if2[HOST_B_IP] = HOST_B_MAC
    
    # Connect all device to simulator
    host_a.attach(sim)
    host_b.attach(sim)
    router_r1.attach(sim)
    
    return sim, host_a, router_r1, host_b
