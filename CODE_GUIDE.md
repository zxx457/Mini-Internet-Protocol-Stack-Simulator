# Code Understanding Guide
## CITS3002 Mini Internet Protocol Stack Project

This document explain all code in simple English.
Help you understand what each part does.

---

## Table of Contents
1. [Project Overview](#project-overview)
2. [Network Topology](#network-topology)
3. [File Explanations](#file-explanations)
4. [How Data Flows](#how-data-flows)
5. [Important Concepts](#important-concepts)
6. [Testing Guide](#testing-guide)

---

## Project Overview

### What We Made
We made a program that simulate network communication.
It send data from Host A to Host B through Router R1.

### Why We Made This
- Learn how internet protocol work
- Understand Layer 2, 3, 4 of network stack
- Practice reliable data transfer (rdt2.2)

### Main Features
- **Segmentation**: Big data split into 500 byte pieces
- **Reliable Transfer**: Use sequence number 0 and 1
- **Routing**: Router forward packet between network
- **MAC Learning**: Remember MAC address automatically

---

## Network Topology

### The Network We Built

```
     Network 1                              Network 2
   (10.0.1.0/24)                          (10.0.2.0/24)

   [Host A]  ----------  [Router R1]  ----------  [Host B]
   10.0.1.10          if1: 10.0.1.1            10.0.2.20
   AA:AA:AA:AA:AA:AA      BB:BB:BB:BB:BB:BB      DD:DD:DD:DD:DD:DD
                      if2: 10.0.2.1
                           CC:CC:CC:CC:CC:CC
```

### Device Information

**Host A:**
- IP Address: 10.0.1.10
- MAC Address: AA:AA:AA:AA:AA:AA
- Connected to: Network 1

**Router R1:**
- Interface 1 IP: 10.0.1.1
- Interface 1 MAC: BB:BB:BB:BB:BB:BB
- Interface 2 IP: 10.0.2.1
- Interface 2 MAC: CC:CC:CC:CC:CC:CC
- Job: Connect Network 1 and Network 2

**Host B:**
- IP Address: 10.0.2.20
- MAC Address: DD:DD:DD:DD:DD:DD
- Connected to: Network 2

---

## File Explanations

### 1. config.py (Person A)

**What it does:**
This file store all network configuration.

**Important Parts:**

#### IP Addresses
```python
HOST_A_IP = "10.0.1.10"      # Host A's IP
HOST_B_IP = "10.0.2.20"      # Host B's IP
R1_IF1_IP = "10.0.1.1"       # Router Interface 1 IP
R1_IF2_IP = "10.0.2.1"       # Router Interface 2 IP
```

#### MAC Addresses
```python
HOST_A_MAC = "AA:AA:AA:AA:AA:AA"    # Host A's MAC
HOST_B_MAC = "DD:DD:DD:DD:DD:DD"    # Host B's MAC
R1_IF1_MAC = "BB:BB:BB:BB:BB:BB"    # Router Interface 1 MAC
R1_IF2_MAC = "CC:CC:CC:CC:CC:CC"    # Router Interface 2 MAC
```

#### Routing Tables
These table tell device where to send packet.

**Host A Routing Table:**
```python
ROUTING_TABLE_HOST_A = (
    RoutingEntry("0.0.0.0", 0, "10.0.1.1", "if0"),
)
```
Meaning: Send all packet to 10.0.1.1 (Router)

**Router R1 Routing Table:**
```python
ROUTING_TABLE_R1 = (
    RoutingEntry("10.0.1.0", 24, None, "if1"),      # Network 1 → Interface 1
    RoutingEntry("10.0.2.0", 24, None, "if2"),      # Network 2 → Interface 2
)
```
Meaning: 
- If destination is in 10.0.1.0/24 → use Interface 1
- If destination is in 10.0.2.0/24 → use Interface 2

#### Important Constants
```python
MAX_SEGMENT_DATA = 500       # Maximum data in one segment
DEFAULT_TTL = 100           # Packet start with TTL=100
DEFAULT_SRC_PORT = 5000     # Source port number
DEFAULT_DST_PORT = 6000     # Destination port number
```

#### longest_prefix_match() Function
```python
def longest_prefix_match(ip, table):
    """
    Find best route for IP address.
    Choose route with longest matching prefix.
    """
```

**Example:**
- IP: 10.0.2.20
- Table: [10.0.0.0/8, 10.0.2.0/24]
- Result: Choose 10.0.2.0/24 (longer match)

---

### 2. protocol.py (Person A)

**What it does:**
This file define protocol structure for Layer 2, 3, 4.

#### EthernetFrame Class (Layer 2)

**What it is:**
Frame is like   n                    
for packet in Layer                      2.

```python
class EthernetFrame:
    dst_mac: str        # Where to send (MAC address)
    src_mac: str        # Who send it (MAC address)
    ether_type: int     # What inside (0x0800 = IPv4)
    payload: bytes      # The IP packet inside
```

**Example:**
```python
frame = EthernetFrame(
    dst_mac="BB:BB:BB:BB:BB:BB",      # Send to Router
    src_mac="AA:AA:AA:AA:AA:AA",      # From Host A
    ether_type=0x0800,                # IPv4 packet
    payload=ip_packet_bytes           # IP packet
)
```

**Methods:**
- `to_bytes()`: Convert frame object to bytes for sending
- `from_bytes()`: Convert bytes back to frame object

#### IPPacket Class (Layer 3)

**What it is:**
Packet is like envelope for segment in Layer 3.

```python
class IPPacket:
    src_ip: str         # Source IP address
    dst_ip: str         # Destination IP address
    ttl: int           # Time To Live (decrease each router)
    protocol: int      # What inside (17 = UDP)
    payload: bytes     # The UDP segment inside
```

**Example:**
```python
packet = IPPacket(
    src_ip="10.0.1.10",           # From Host A
    dst_ip="10.0.2.20",           # To Host B
    ttl=100,                      # Start with 100
    protocol=17,                  # UDP protocol
    payload=udp_segment_bytes     # UDP segment
)
```

**Important: TTL (Time To Live)**
- Start with 100
- Each router decrease by 1
- If become 0, packet is dropped
- Prevent infinite loop

#### UDPSegment Class (Layer 4)

**What it is:**
Segment contain actual data in Layer 4.

```python
class UDPSegment:
    src_port: int           # Source port (5000)
    dst_port: int           # Destination port (6000)
    segment_type: int       # DATA (0) or ACK (1)
    sequence_number: int    # 0 or 1 for rdt2.2
    data: bytes            # Actual application data
```

**Example DATA segment:**
```python
segment = UDPSegment(
    src_port=5000,
    dst_port=6000,
    segment_type=0,              # DATA
    sequence_number=0,           # seq=0
    data=b"XXXXXXXXXX"          # 10 bytes
)
```

**Example ACK segment:**
```python
ack = UDPSegment(
    src_port=6000,
    dst_port=5000,
    segment_type=1,              # ACK
    sequence_number=0,           # ACK for seq=0
    data=b""                    # No data in ACK
)
```

---

### 3. devices.py (Person B - You!)

**What it does:**
This file implement all network device logic.
This is the main file you wrote!

---

#### Simulator Class

**What it does:**
Act like network cable. Send frame to correct device.

```python
class Simulator:
    def __init__(self):
        self.mac_handlers = {}    # Store MAC → handler
```

**How it work:**

**Step 1: Register device**
```python
sim.register_mac("AA:AA:AA:AA:AA:AA", host_a.recv_frame)
```
Meaning: When frame go to AA:AA:AA:AA:AA:AA, call host_a.recv_frame()

**Step 2: Send frame**
```python
sim.send_frame(frame_bytes)
```
What happen:
1. Parse frame to get destination MAC
2. Find handler for that MAC
3. Call handler with frame bytes

**Example:**
```
frame.dst_mac = "BB:BB:BB:BB:BB:BB"
→ Find handler for BB:BB
→ Call router.recv_on_interface()
```

---

#### Host Class

**What it does:**
Implement complete network stack (Layer 2, 3, 4).

**Attributes:**
```python
class Host:
    # Basic info
    name: str              # "Host A" or "Host B"
    ip: str               # IP address
    mac: str              # MAC address
    route_table: tuple    # Routing table
    arp_map: dict         # IP → MAC mapping
    sim: Simulator        # Reference to simulator
    
    # rdt2.2 state
    current_seq: int      # Current sequence (0 or 1)
    expect_seq: int       # Expected sequence (0 or 1)
    sender_ip: str        # Remember who send DATA
```

---

##### Layer 4 Methods (Transport Layer)

**Method 1: send_data()**
```python
def send_data(self, dest_ip, app_data):
    """
    Send data to destination.
    Split big data into 500 byte segments.
    """
```

**What it does:**
1. Receive data from application
2. Split into pieces (max 500 bytes each)
3. Send each piece one by one

**Example:**
```python
# Send 1000 bytes
data = b"X" * 1000

# Split into:
# Segment 1: bytes 0-499   (500 bytes)
# Segment 2: bytes 500-999 (500 bytes)

# Send segment 1 → wait → send segment 2
```

**Code explanation:**
```python
# Make segments list
seg_list = []
pos = 0
while pos < len(app_data):
    piece = app_data[pos:pos+MAX_SEGMENT_DATA]  # Get 500 bytes
    seg_list.append(piece)
    pos += MAX_SEGMENT_DATA                     # Move to next 500

# Send all segments
for seg_data in seg_list:
    self.send_one_segment(seg_data, dest_ip)
```

---

**Method 2: send_one_segment()**
```python
def send_one_segment(self, seg_data, dest_ip):
    """
    Send one segment with current sequence number.
    """
```

**What it does:**
1. Create UDP segment with DATA type
2. Use current sequence number (0 or 1)
3. Send to network layer
4. Change sequence number for next time

**Step by step:**
```python
# Step 1: Create segment
segment = UDPSegment(
    src_port=5000,
    dst_port=6000,
    segment_type=SEGMENT_TYPE_DATA,    # This is DATA
    sequence_number=self.current_seq,   # Use 0 or 1
    data=seg_data                       # The 500 bytes
)

# Step 2: Convert to bytes
seg_bytes = segment.to_bytes()

# Step 3: Send to Layer 3
self.send_to_net_layer(seg_bytes, dest_ip)

# Step 4: Change sequence (0→1 or 1→0)
self.current_seq = 1 - self.current_seq
```

**Sequence number pattern:**
```
Send segment 1: seq=0  →  current_seq = 1 - 0 = 1
Send segment 2: seq=1  →  current_seq = 1 - 1 = 0
Send segment 3: seq=0  →  current_seq = 1 - 0 = 1
...
```

---

**Method 3: recv_from_net_layer()**
```python
def recv_from_net_layer(self, seg_bytes):
    """
    Receive segment from network layer.
    Process DATA or ACK.
    """
```

**What it does:**
Handle two type of segment: DATA and ACK.

**Case 1: Receive DATA segment**
```python
if segment.segment_type == SEGMENT_TYPE_DATA:
    # Check sequence number
    if segment.sequence_number == self.expect_seq:
        # Correct sequence! Process it.
        
        # 1. Deliver data to application
        print("DATA segment delivered to Application Layer")
        
        # 2. Create ACK with same sequence number
        ack = UDPSegment(
            segment_type=SEGMENT_TYPE_ACK,
            sequence_number=self.expect_seq
        )
        
        # 3. Send ACK back to sender
        self.send_to_net_layer(ack_bytes, self.sender_ip)
        
        # 4. Update expected sequence for next time
        self.expect_seq = 1 - self.expect_seq
```

**Example:**
```
Receive: DATA seq=0
expect_seq=0 → Match! ✓
→ Deliver data
→ Send ACK seq=0
→ expect_seq = 1 (for next DATA)
```

**Case 2: Receive ACK segment**
```python
elif segment.segment_type == SEGMENT_TYPE_ACK:
    # Just log it
    print(f"ACK received: seq={segment.sequence_number}")
```

---

##### Layer 3 Methods (Network Layer)

**Method 1: send_to_net_layer()**
```python
def send_to_net_layer(self, segment_bytes, dest_ip):
    """
    Create IP packet and send to Layer 2.
    """
```

**What it does:**
1. Create IP packet with segment inside
2. Find next hop using routing table
3. Send to data link layer

**Step by step:**
```python
# Step 1: Create IP packet
ip_packet = IPPacket(
    src_ip=self.ip,              # My IP
    dst_ip=dest_ip,              # Destination IP
    ttl=DEFAULT_TTL,             # Start with 100
    protocol=IP_PROTOCOL_UDP,    # UDP protocol
    payload=segment_bytes        # UDP segment
)

# Step 2: Find next hop
route_entry = longest_prefix_match(dest_ip, self.route_table)
next_ip = route_entry.next_hop_ip

# Step 3: Send to Layer 2
packet_bytes = ip_packet.to_bytes()
self.send_frame_out(packet_bytes, next_ip)
```

**Example for Host A:**
```
dest_ip = 10.0.2.20 (Host B)
Routing table: Send all to 10.0.1.1
→ next_ip = 10.0.1.1 (Router)
→ Send to Router, not directly to Host B!
```

---

**Method 2: recv_from_link_layer()**
```python
def recv_from_link_layer(self, packet_bytes):
    """
    Receive IP packet from Layer 2.
    Check if packet is for me.
    """
```

**What it does:**
1. Parse IP packet
2. Check destination IP
3. If for me → deliver to Layer 4
4. If not for me → ignore

**Code:**
```python
# Parse packet
ip_packet = IPPacket.from_bytes(packet_bytes)

# Check destination
if ip_packet.dst_ip == self.ip:
    # This packet is for me!
    
    # Remember sender for ACK reply
    self.sender_ip = ip_packet.src_ip
    
    # Deliver to Layer 4
    self.recv_from_net_layer(ip_packet.payload)
```

**Example:**
```
Host B receive packet:
dst_ip = 10.0.2.20
Host B's IP = 10.0.2.20
→ Match! Process it.

src_ip = 10.0.1.10
→ sender_ip = 10.0.1.10 (for ACK reply)
```

---

##### Layer 2 Methods (Data Link Layer)

**Method 1: send_frame_out()**
```python
def send_frame_out(self, packet_bytes, next_hop_ip):
    """
    Create ethernet frame and send.
    """
```

**What it does:**
1. Find MAC address for next hop IP
2. Create ethernet frame
3. Send through simulator

**Step by step:**
```python
# Step 1: Find MAC address using ARP table
dest_mac = self.arp_map.get(next_hop_ip)

# Step 2: Create frame
eth_frame = EthernetFrame(
    dst_mac=dest_mac,         # Destination MAC
    src_mac=self.mac,         # My MAC
    ether_type=ETHERTYPE_IPV4,  # IPv4
    payload=packet_bytes      # IP packet
)

# Step 3: Send
if self.sim:
    self.sim.send_frame(eth_frame.to_bytes())
```

**Example:**
```
next_hop_ip = 10.0.1.1 (Router)
ARP table: 10.0.1.1 → BB:BB:BB:BB:BB:BB
→ dest_mac = BB:BB:BB:BB:BB:BB
→ Create frame to Router's MAC
```

---

**Method 2: recv_frame()**
```python
def recv_frame(self, frame_bytes):
    """
    Receive ethernet frame.
    """
```

**What it does:**
1. Parse frame
2. Learn source MAC (remember it)
3. Deliver packet to Layer 3

**Code:**
```python
# Parse frame
eth_frame = EthernetFrame.from_bytes(frame_bytes)

# Learn MAC (just log, not actually store in Host)
print(f"Source MAC learned: {eth_frame.src_mac}")

# Deliver packet to Layer 3
self.recv_from_link_layer(eth_frame.payload)
```

---

#### Router Class

**What it does:**
Forward packet between two network.

**Attributes:**
```python
class Router:
    # Basic info
    name: str              # "Router R1"
    if1_ip: str           # Interface 1 IP
    if1_mac: str          # Interface 1 MAC
    if2_ip: str           # Interface 2 IP
    if2_mac: str          # Interface 2 MAC
    route_table: tuple    # Routing table
    sim: Simulator        # Simulator reference
    
    # MAC learning tables (Important!)
    mac_table_if1: dict   # Interface 1: IP → MAC
    mac_table_if2: dict   # Interface 2: IP → MAC
```

**Why two MAC tables?**
- Interface 1 connect to Network 1
- Interface 2 connect to Network 2
- Each network has different devices
- Must keep them separate!

---

##### Layer 3 Method

**Method: do_forwarding()**
```python
def do_forwarding(self, packet_bytes):
    """
    Forward packet to destination.
    """
```

**What it does:**
1. Parse IP packet
2. Decrease TTL
3. Check if TTL is 0
4. Find route
5. Forward to output interface

**Step by step:**
```python
# Step 1: Parse packet
ip_packet = IPPacket.from_bytes(packet_bytes)

# Step 2: Decrease TTL
old_ttl = ip_packet.ttl
ip_packet.ttl = ip_packet.ttl - 1
print(f"TTL decremented: {old_ttl} → {ip_packet.ttl}")

# Step 3: Check TTL
if ip_packet.ttl == 0:
    print("Packet dropped (TTL expired)")
    return   # Stop! Don't forward

# Step 4: Find route
route_entry = longest_prefix_match(ip_packet.dst_ip, self.route_table)
next_hop_ip = route_entry.next_hop_ip or ip_packet.dst_ip
out_interface = route_entry.outgoing_interface

# Step 5: Find MAC address
if out_interface == "if1":
    dest_mac_addr = self.mac_table_if1.get(next_hop_ip)
else:
    dest_mac_addr = self.mac_table_if2.get(next_hop_ip)

# Step 6: Send
new_packet_bytes = ip_packet.to_bytes()
self.send_on_interface(new_packet_bytes, out_interface, dest_mac_addr)
```

**Example:**
```
Receive packet: dst_ip=10.0.2.20, TTL=100
TTL: 100 → 99
Routing: 10.0.2.0/24 → Interface 2
Next hop: 10.0.2.20
MAC table if2: 10.0.2.20 → DD:DD:DD:DD:DD:DD
→ Send on Interface 2 to DD:DD:DD:DD:DD:DD
```

---

##### Layer 2 Methods

**Method 1: recv_on_interface()**
```python
def recv_on_interface(self, if_name, frame_bytes):
    """
    Receive frame on interface.
    Learn MAC address.
    """
```

**What it does:**
1. Parse frame
2. Learn MAC address (Important!)
3. Forward to Layer 3

**MAC Learning Process:**
```python
# Step 1: Parse frame
eth_frame = EthernetFrame.from_bytes(frame_bytes)

# Step 2: Parse packet to get source IP
ip_packet = IPPacket.from_bytes(eth_frame.payload)

# Step 3: Learn MAC (IP → MAC mapping)
if if_name == "if1":
    # Learn on Interface 1 table
    self.mac_table_if1[ip_packet.src_ip] = eth_frame.src_mac
else:
    # Learn on Interface 2 table
    self.mac_table_if2[ip_packet.src_ip] = eth_frame.src_mac

# Step 4: Forward to Layer 3
self.do_forwarding(eth_frame.payload)
```

**Example:**
```
Interface 1 receive frame:
src_mac = AA:AA:AA:AA:AA:AA
src_ip = 10.0.1.10

Learn: mac_table_if1[10.0.1.10] = AA:AA:AA:AA:AA:AA

Later when send to 10.0.1.10:
→ Use AA:AA:AA:AA:AA:AA from table!
```

**Why MAC learning important?**
- Router need to know MAC for IP address
- Can't just know IP, must know MAC to send frame
- Learn from incoming frame, use for outgoing frame

---

**Method 2: send_on_interface()**
```python
def send_on_interface(self, packet_bytes, if_name, dest_mac_addr):
    """
    Send frame on interface.
    """
```

**What it does:**
1. Choose source MAC based on interface
2. Create frame
3. Send

**Code:**
```python
# Step 1: Choose source MAC
if if_name == "if1":
    source_mac = self.if1_mac    # BB:BB:BB:BB:BB:BB
else:
    source_mac = self.if2_mac    # CC:CC:CC:CC:CC:CC

# Step 2: Create frame
eth_frame = EthernetFrame(
    dst_mac=dest_mac_addr,
    src_mac=source_mac,       # Different MAC for each interface!
    ether_type=ETHERTYPE_IPV4,
    payload=packet_bytes
)

# Step 3: Send
self.sim.send_frame(eth_frame.to_bytes())
```

**Why different source MAC?**
- Each interface is different "network card"
- Network 1 see Router as BB:BB:BB:BB:BB:BB
- Network 2 see Router as CC:CC:CC:CC:CC:CC

---

#### build_topology() Function

**What it does:**
Create all device and connect them.

**Code:**
```python
def build_topology():
    # Step 1: Create simulator
    sim = Simulator()
    
    # Step 2: Create Host A
    host_a = Host(
        host_name="Host A",
        ip_addr="10.0.1.10",
        mac_addr="AA:AA:AA:AA:AA:AA",
        route_table=ROUTING_TABLE_HOST_A,
        arp_map=dict(ARP_SEED_HOST_A)
    )
    
    # Step 3: Create Host B
    host_b = Host(
        host_name="Host B",
        ip_addr="10.0.2.20",
        mac_addr="DD:DD:DD:DD:DD:DD",
        route_table=ROUTING_TABLE_HOST_B,
        arp_map=dict(ARP_SEED_HOST_B)
    )
    
    # Step 4: Create Router
    router_r1 = Router(
        router_name="Router R1",
        if1_ip_addr="10.0.1.1",
        if1_mac_addr="BB:BB:BB:BB:BB:BB",
        if2_ip_addr="10.0.2.1",
        if2_mac_addr="CC:CC:CC:CC:CC:CC",
        route_table=ROUTING_TABLE_R1
    )
    
    # Step 5: Pre-fill router MAC tables
    # (So router know host MAC from beginning)
    router_r1.mac_table_if1[HOST_A_IP] = HOST_A_MAC
    router_r1.mac_table_if2[HOST_B_IP] = HOST_B_MAC
    
    # Step 6: Connect all to simulator
    host_a.attach(sim)
    host_b.attach(sim)
    router_r1.attach(sim)
    
    # Step 7: Return everything
    return sim, host_a, router_r1, host_b
```

---

### 4. main.py (Person B - You!)

**What it does:**
Start the program and send data.

**Code:**
```python
def main():
    # Step 1: Check command line argument
    if len(sys.argv) != 2:
        print("Usage: python main.py <message_size>")
        return 1
    
    # Step 2: Get message size
    try:
        size = int(sys.argv[1])
    except ValueError:
        print("Error: message_size must be number")
        return 1
    
    # Step 3: Build network
    sim, host_a, router, host_b = build_topology()
    
    # Step 4: Create data
    data = b"X" * size
    
    # Step 5: Send data from Host A to Host B
    host_a.send_data(HOST_B_IP, data)
    
    # Step 6: Done!
    print("\n=== Transmission Complete ===")
    return 0

if __name__ == "__main__":
    exit(main())
```

**How to run:**
```bash
python main.py 10       # Send 10 bytes
python main.py 1000     # Send 1000 bytes
```

---

## How Data Flows

### Example: Send 10 Bytes

Let me explain step by step what happen when we run:
```bash
python main.py 10
```

---

#### Phase 1: Application Layer

**Step 1: main.py create data**
```python
data = b"XXXXXXXXXX"  # 10 bytes
```

**Step 2: Start transmission**
```python
host_a.send_data(HOST_B_IP, data)
# HOST_B_IP = "10.0.2.20"
```

---

#### Phase 2: Host A - Layer 4 (Transport)

**Step 3: send_data() split data**
```python
# 10 bytes < 500 bytes
# So only 1 segment needed
segments = [b"XXXXXXXXXX"]
```

**Step 4: send_one_segment()**
```python
# Create UDP segment
segment = UDPSegment(
    segment_type=DATA,
    sequence_number=0,      # Start with seq=0
    data=b"XXXXXXXXXX"
)

# Send to Layer 3
send_to_net_layer(segment_bytes, "10.0.2.20")

# Update sequence
current_seq = 1  # Next will be seq=1
```

**Log:**
```
Host A: Layer 4: Data received from Application Layer. Data size=10
Host A: Layer 4: Segment created by adding transport layer header (DATA, seq=0)
Host A: Layer 4: Segment sent to Network Layer
```

---

#### Phase 3: Host A - Layer 3 (Network)

**Step 5: send_to_net_layer()**
```python
# Create IP packet
packet = IPPacket(
    src_ip="10.0.1.10",     # Host A IP
    dst_ip="10.0.2.20",     # Host B IP
    ttl=100,                # Start TTL
    payload=segment_bytes
)

# Find next hop
# Routing table: Send all to 10.0.1.1 (Router)
next_hop = "10.0.1.1"

# Send to Layer 2
send_frame_out(packet_bytes, "10.0.1.1")
```

**Log:**
```
Host A: Layer 3: Segment received from Transport Layer: SRC_IP=10.0.1.10, DST_IP=10.0.2.20, TTL=100
Host A: Layer 3: Routing table lookup performed
Host A: Layer 3: Next-hop IP determined: 10.0.1.1
Host A: Layer 3: Packet forwarded to Data Link Layer
```

---

#### Phase 4: Host A - Layer 2 (Data Link)

**Step 6: send_frame_out()**
```python
# Find MAC for next hop IP
# ARP table: 10.0.1.1 → BB:BB:BB:BB:BB:BB
dest_mac = "BB:BB:BB:BB:BB:BB"

# Create frame
frame = EthernetFrame(
    dst_mac="BB:BB:BB:BB:BB:BB",    # Router MAC
    src_mac="AA:AA:AA:AA:AA:AA",    # Host A MAC
    payload=packet_bytes
)

# Send through simulator
sim.send_frame(frame_bytes)
```

**Log:**
```
Host A: Layer 2: Packet received from Network Layer
Host A: Layer 2: Destination MAC lookup for next-hop IP (10.0.1.1) → BB:BB:BB:BB:BB:BB
Host A: Layer 2: Frame created: SRC_MAC=AA:AA:AA:AA:AA:AA, DST_MAC=BB:BB:BB:BB:BB:BB
Host A: Layer 2: Frame sent
```

---

#### Phase 5: Simulator

**Step 7: Deliver frame to Router**
```python
# Parse frame
dst_mac = "BB:BB:BB:BB:BB:BB"

# Find handler
handler = mac_handlers["BB:BB:BB:BB:BB:BB"]
# This is router.recv_on_interface("if1")

# Call handler
handler(frame_bytes)
```

---

#### Phase 6: Router - Layer 2 (Interface 1)

**Step 8: recv_on_interface("if1")**
```python
# Parse frame
frame = EthernetFrame.from_bytes(frame_bytes)
# src_mac = "AA:AA:AA:AA:AA:AA"

# Parse packet to get IP
packet = IPPacket.from_bytes(frame.payload)
# src_ip = "10.0.1.10"

# Learn MAC on Interface 1
mac_table_if1["10.0.1.10"] = "AA:AA:AA:AA:AA:AA"

# Forward to Layer 3
do_forwarding(frame.payload)
```

**Log:**
```
Router R1: Layer 2: Frame received on Interface 1
Router R1: Layer 2: Source MAC learned: AA:AA:AA:AA:AA:AA on Interface 1
Router R1: Layer 2: Packet delivered to Network Layer
```

---

#### Phase 7: Router - Layer 3

**Step 9: do_forwarding()**
```python
# Parse packet
packet = IPPacket.from_bytes(packet_bytes)
# dst_ip = "10.0.2.20", ttl = 100

# Decrease TTL
packet.ttl = 99

# Find route
# Routing table: 10.0.2.0/24 → Interface 2
next_hop = "10.0.2.20"      # Directly to Host B
out_interface = "if2"

# Find MAC from Interface 2 table
dest_mac = mac_table_if2["10.0.2.20"]
# = "DD:DD:DD:DD:DD:DD"

# Send on Interface 2
send_on_interface(packet_bytes, "if2", "DD:DD:DD:DD:DD:DD")
```

**Log:**
```
Router R1: Layer 3: Packet received from Data Link Layer: SRC_IP=10.0.1.10, DST_IP=10.0.2.20, TTL=100
Router R1: Layer 3: TTL decremented: 100 → 99
Router R1: Layer 3: Routing table lookup performed
Router R1: Layer 3: Next-hop IP determined: 10.0.2.20
Router R1: Layer 3: Outgoing interface selected (Interface 2)
Router R1: Layer 3: Packet forwarded to Data Link Layer
```

---

#### Phase 8: Router - Layer 2 (Interface 2)

**Step 10: send_on_interface("if2")**
```python
# Choose source MAC for Interface 2
source_mac = "CC:CC:CC:CC:CC:CC"

# Create frame
frame = EthernetFrame(
    dst_mac="DD:DD:DD:DD:DD:DD",    # Host B MAC
    src_mac="CC:CC:CC:CC:CC:CC",    # Router Interface 2 MAC
    payload=packet_bytes
)

# Send
sim.send_frame(frame_bytes)
```

**Log:**
```
Router R1: Layer 2: Packet received from Network Layer
Router R1: Layer 2: Destination MAC lookup for next-hop IP → DD:DD:DD:DD:DD:DD
Router R1: Layer 2: Frame created: SRC_MAC=CC:CC:CC:CC:CC:CC, DST_MAC=DD:DD:DD:DD:DD:DD
Router R1: Layer 2: Frame forwarded on Interface 2
```

---

#### Phase 9: Simulator (Again)

**Step 11: Deliver to Host B**
```python
# dst_mac = "DD:DD:DD:DD:DD:DD"
# handler = host_b.recv_frame
handler(frame_bytes)
```

---

#### Phase 10: Host B - Layer 2

**Step 12: recv_frame()**
```python
# Parse frame
frame = EthernetFrame.from_bytes(frame_bytes)
# src_mac = "CC:CC:CC:CC:CC:CC"

# Learn MAC
print("Source MAC learned: CC:CC:CC:CC:CC:CC")

# Deliver to Layer 3
recv_from_link_layer(frame.payload)
```

**Log:**
```
Host B: Layer 2: Frame received
Host B: Layer 2: Source MAC learned: CC:CC:CC:CC:CC:CC
Host B: Layer 2: Packet delivered to Network Layer
```

---

#### Phase 11: Host B - Layer 3

**Step 13: recv_from_link_layer()**
```python
# Parse packet
packet = IPPacket.from_bytes(packet_bytes)
# src_ip = "10.0.1.10"
# dst_ip = "10.0.2.20"
# ttl = 99

# Check destination
if packet.dst_ip == "10.0.2.20":  # My IP!
    # Remember sender for ACK
    sender_ip = "10.0.1.10"
    
    # Deliver to Layer 4
    recv_from_net_layer(packet.payload)
```

**Log:**
```
Host B: Layer 3: Packet received from Data Link Layer: SRC_IP=10.0.1.10, DST_IP=10.0.2.20, TTL=99
Host B: Layer 3: Packet identified as local delivery
Host B: Layer 3: Segment delivered to Transport Layer
```

---

#### Phase 12: Host B - Layer 4

**Step 14: recv_from_net_layer()**
```python
# Parse segment
segment = UDPSegment.from_bytes(seg_bytes)
# segment_type = DATA
# sequence_number = 0
# data = b"XXXXXXXXXX"

# Check type
if segment_type == DATA:
    # Check sequence
    if segment.sequence_number == expect_seq:  # 0 == 0 ✓
        # Deliver data
        print("DATA segment delivered to Application Layer. Data size=10")
        
        # Create ACK
        ack = UDPSegment(
            segment_type=ACK,
            sequence_number=0,     # ACK for seq=0
            data=b""
        )
        
        # Send ACK back to 10.0.1.10
        send_to_net_layer(ack_bytes, "10.0.1.10")
        
        # Update expected
        expect_seq = 1  # Next expect seq=1
```

**Log:**
```
Host B: Layer 4: Segment received from Network Layer
Host B: Layer 4: Checksum verified
Host B: Layer 4: DATA segment delivered to Application Layer. Data size=10
Host B: Layer 4: Segment created by adding transport layer header (ACK, seq=0)
Host B: Layer 4: Segment sent to Network Layer
```

---

#### Phase 13: ACK Return Path

**Step 15-22: ACK go back**
ACK travel from Host B → Router → Host A
Same process but reverse direction!

**Host B → Router:**
- Layer 4: Create ACK segment
- Layer 3: Create IP packet (dst=10.0.1.10)
- Layer 2: Create frame (dst=CC:CC:CC:CC:CC:CC Router MAC)
- Send through simulator

**Router:**
- Interface 2 receive
- Learn MAC for Host B
- TTL decrease
- Forward to Interface 1

**Router → Host A:**
- Layer 2: Create frame (dst=AA:AA:AA:AA:AA:AA Host A MAC)
- Send through simulator

**Host A receive:**
- Layer 2: Receive frame
- Layer 3: Check destination (my IP!)
- Layer 4: Receive ACK

---

#### Phase 14: Host A Receive ACK

**Step 23: Final ACK processing**
```python
# At Host A Layer 4
segment = UDPSegment.from_bytes(seg_bytes)

if segment.segment_type == ACK:
    print(f"ACK received: seq=0")
```

**Log:**
```
Host A: Layer 4: ACK received: seq=0
```

**Done! ✅**

---

### Visual Summary

```
Application:  [10 bytes data]
                    ↓
Host A L4:    [UDP: DATA seq=0 | 10 bytes]
                    ↓
Host A L3:    [IP: src=10.0.1.10, dst=10.0.2.20, TTL=100 | UDP segment]
                    ↓
Host A L2:    [Ethernet: src=AA:AA, dst=BB:BB | IP packet]
                    ↓
Simulator:    → Router R1
                    ↓
Router L2:    Learn: 10.0.1.10 = AA:AA
                    ↓
Router L3:    TTL: 100 → 99, Route → Interface 2
                    ↓
Router L2:    [Ethernet: src=CC:CC, dst=DD:DD | IP packet]
                    ↓
Simulator:    → Host B
                    ↓
Host B L2:    Learn: CC:CC
                    ↓
Host B L3:    Check: dst=10.0.2.20 (my IP!) ✓
                    ↓
Host B L4:    Check: seq=0, expect=0 ✓
              Deliver 10 bytes to Application
              Create ACK seq=0
                    ↓
ACK Return:   Host B → Router → Host A
                    ↓
Host A L4:    ACK received: seq=0 ✅
```

---

## Important Concepts

### 1. Encapsulation

**What it is:**
Add header at each layer.

**Example:**
```
Layer 4: [UDP Header | Data]
              ↓ encapsulate
Layer 3: [IP Header | UDP Segment]
              ↓ encapsulate
Layer 2: [Ethernet Header | IP Packet]
```

**Like Russian doll:**
- Data is inside UDP
- UDP is inside IP
- IP is inside Ethernet

---

### 2. Decapsulation

**What it is:**
Remove header at each layer when receive.

**Example:**
```
Layer 2: Receive [Ethernet Header | IP Packet]
              ↓ remove Ethernet header
Layer 3: Get [IP Header | UDP Segment]
              ↓ remove IP header
Layer 4: Get [UDP Header | Data]
              ↓ remove UDP header
Application: Get [Data]
```

---

### 3. rdt2.2 Protocol

**What it is:**
Reliable Data Transfer version 2.2
Use sequence number 0 and 1.

**How it work:**

**Sender side:**
```
1. Send DATA seq=0
2. Wait for ACK
3. If ACK seq=0 received → success!
4. Send next DATA seq=1
5. Wait for ACK
6. If ACK seq=1 received → success!
7. Repeat with seq=0, seq=1, seq=0...
```

**Receiver side:**
```
1. Wait for DATA
2. Receive DATA seq=0
3. Check: expect_seq=0 → match!
4. Deliver data to application
5. Send ACK seq=0
6. expect_seq = 1 (for next DATA)
7. Repeat...
```

**Why use 0 and 1?**
- Simple implementation
- Can detect duplicate packet
- Can detect lost packet (not in this project)

---

### 4. Routing

**What it is:**
Decide where to send packet based on destination IP.

**How it work:**

**Routing table format:**
```
(Network, Prefix Length, Next Hop, Interface)
```

**Example table:**
```
10.0.1.0/24 → next_hop=None, interface=if1
10.0.2.0/24 → next_hop=None, interface=if2
```

**Longest prefix match:**
- Find all matching route
- Choose longest prefix (most specific)

**Example:**
```
Destination: 10.0.2.20
Match: 10.0.0.0/8  (match)
Match: 10.0.2.0/24 (match, longer!)
→ Choose 10.0.2.0/24
```

---

### 5. MAC Learning

**What it is:**
Router remember MAC address from incoming frame.

**How it work:**

**Step 1: Frame arrive**
```
Frame: src_mac=AA:AA:AA:AA:AA:AA
Packet inside: src_ip=10.0.1.10
```

**Step 2: Learn**
```
mac_table_if1[10.0.1.10] = AA:AA:AA:AA:AA:AA
```

**Step 3: Use later**
```
Need to send to 10.0.1.10
→ Look up table
→ dest_mac = AA:AA:AA:AA:AA:AA
```

**Why important:**
- Router need MAC to send frame
- Can't just have IP address
- Learn automatically from traffic

---

### 6. TTL (Time To Live)

**What it is:**
Number that decrease each time packet go through router.

**Purpose:**
Prevent infinite loop.

**How it work:**
```
Host A: Create packet with TTL=100
Router R1: Receive → TTL=99
Router R2: Receive → TTL=98
...
Router R100: Receive → TTL=0 → DROP!
```

**In our project:**
- Host create: TTL=100
- Router decrease: TTL=99
- Host receive: TTL=99

---

### 7. Segmentation

**What it is:**
Split big data into small piece.

**Why need:**
- Network has maximum packet size
- Our limit: 500 bytes per segment

**Example:**
```
Data: 1000 bytes

Split into:
Segment 1: bytes 0-499   (500 bytes, seq=0)
Segment 2: bytes 500-999 (500 bytes, seq=1)
```

**Send process:**
1. Send segment 1 → wait ACK
2. Receive ACK for segment 1
3. Send segment 2 → wait ACK
4. Receive ACK for segment 2
5. Done!

---

### 8. ARP Table

**What it is:**
Table that map IP address to MAC address.

**Format:**
```
IP Address  →  MAC Address
10.0.1.1   →  BB:BB:BB:BB:BB:BB
10.0.2.1   →  CC:CC:CC:CC:CC:CC
```

**In our project:**
- Pre-configured in config.py
- Not learn automatically (only in Host)
- Router use MAC learning instead

---

## Testing Guide

### How to Test

**Basic test:**
```bash
python main.py 10
```

**Expected output:**
```
Host A: Layer 4: Data received from Application Layer. Data size=10
Host A: Layer 4: Segment created by adding transport layer header (DATA, seq=0)
...
Host B: Layer 4: DATA segment delivered to Application Layer. Data size=10
...
Host A: Layer 4: ACK received: seq=0

=== Transmission Complete ===
```

---

### Test Cases

**Test 1: 10 bytes (1 segment)**
```bash
python main.py 10
```
**Check:**
- ✅ One DATA segment (seq=0)
- ✅ One ACK (seq=0)
- ✅ TTL: 100 → 99

---

**Test 2: 500 bytes (1 segment)**
```bash
python main.py 500
```
**Check:**
- ✅ One DATA segment (seq=0)
- ✅ Data size=500
- ✅ One ACK

---

**Test 3: 1000 bytes (2 segments)**
```bash
python main.py 1000
```
**Check:**
- ✅ Two DATA segments (seq=0, seq=1)
- ✅ Two ACKs (seq=0, seq=1)
- ✅ First segment: 500 bytes
- ✅ Second segment: 500 bytes

---

**Test 4: 1500 bytes (3 segments)**
```bash
python main.py 1500
```
**Check:**
- ✅ Three DATA segments (seq=0, seq=1, seq=0)
- ✅ Three ACKs
- ✅ Sequence alternate: 0, 1, 0

---

### What to Look For

**Correct sequence:**
```
DATA seq=0 → ACK seq=0 → DATA seq=1 → ACK seq=1
```

**TTL change:**
```
Host A create: TTL=100
Router process: TTL=100 → 99
Host B receive: TTL=99
```

**MAC learning:**
```
Router R1: Source MAC learned: AA:AA:AA:AA:AA:AA on Interface 1
Router R1: Source MAC learned: DD:DD:DD:DD:DD:DD on Interface 2
```

**Routing:**
```
Host A: Next-hop IP determined: 10.0.1.1
Router R1: Next-hop IP determined: 10.0.2.20
```

---

## Common Questions

### Q1: Why sequence use 0 and 1 only?

**Answer:**
rdt2.2 protocol use alternating bit.
Only need 2 number to alternate.
0 → 1 → 0 → 1 → 0 ...

Not need 0, 1, 2, 3... because we send one segment at a time.
Wait for ACK before send next.

---

### Q2: Why router have two MAC table?

**Answer:**
Each interface connect to different network.
Must keep them separate!

Example:
- Interface 1: Network 1 (10.0.1.0/24)
  - Has Host A
- Interface 2: Network 2 (10.0.2.0/24)
  - Has Host B

If mix together, might send to wrong network!

---

### Q3: What happen if TTL become 0?

**Answer:**
Router drop the packet.
Not forward it.
This prevent infinite loop.

In real internet, TTL usually start at 64 or 128.

---

### Q4: Why need ARP table?

**Answer:**
We need both IP and MAC:
- IP for routing (Layer 3)
- MAC for frame delivery (Layer 2)

ARP table map IP → MAC.
So we can find MAC when we have IP.

---

### Q5: Can Host A send directly to Host B?

**Answer:**
No! They in different network.

Host A in 10.0.1.0/24
Host B in 10.0.2.0/24

Must go through Router R1.

This is why routing table say:
"Send all packet to 10.0.1.1 (Router)"

---

### Q6: What if segment bigger than 500 bytes?

**Answer:**
Not possible in our code!

send_data() function split data:
```python
while pos < len(data):
    piece = data[pos:pos+500]  # Max 500 bytes
    segments.append(piece)
    pos += 500
```

Every segment is ≤ 500 bytes.

---

### Q7: Why Host B remember sender_ip?

**Answer:**
For sending ACK back!

When Host B receive DATA:
- Remember: sender_ip = 10.0.1.10
- Later create ACK
- Send ACK to sender_ip

Without this, don't know where to send ACK!

---

## Summary

### What You Made

**5 Files:**
1. config.py - Network setup (Person A)
2. protocol.py - Protocol structure (Person A)
3. devices.py - Main logic (Person B - YOU!)
4. main.py - Start program (Person B - YOU!)
5. README.md - Documentation (Person B - YOU!)

**3 Classes:**
1. Simulator - Deliver frame
2. Host - Complete network stack (Layer 2, 3, 4)
3. Router - Forward between network

**Key Features:**
- ✅ rdt2.2 protocol (sequence 0, 1)
- ✅ Segmentation (500 bytes)
- ✅ Routing (find next hop)
- ✅ MAC learning (remember MAC address)
- ✅ TTL handling (decrease at router)

---

### Your Contribution

**You implemented:**
- Host class (200 lines)
  - Layer 4: send_data, send_one_segment, recv_from_net_layer
  - Layer 3: send_to_net_layer, recv_from_link_layer
  - Layer 2: send_frame_out, recv_frame

- Router class (150 lines)
  - Layer 3: do_forwarding
  - Layer 2: recv_on_interface, send_on_interface

- Simulator class (30 lines)
- build_topology function (40 lines)
- main.py (39 lines)

**Total: ~460 lines of code!**

---

### Understanding Checklist

Can you explain:
- ✅ What each layer do?
- ✅ How data flow from Host A to Host B?
- ✅ Why use sequence number 0 and 1?
- ✅ How MAC learning work?
- ✅ Why TTL decrease at router?
- ✅ How routing table used?

If yes → You understand the code! ✅

---

## Good Luck! 🎉

This is your code. You made it!
Understand it well for presentation.

**Remember:**
- Person A give you framework (config, protocol)
- You implement all device logic
- You make it work!

**Be confident!** 💪
