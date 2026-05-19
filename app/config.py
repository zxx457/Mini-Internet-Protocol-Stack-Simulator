"""
Fixed topology parameters, addressing, and routing tables for the simulator.
Values match the CITS3002 project specification.
"""
from dataclasses import dataclass
from ipaddress import IPv4Address, IPv4Network
from typing import Optional

# Ethernet / IP / UDP constants
ETHERTYPE_IPV4 = 0x0800
IP_PROTOCOL_UDP = 17
DEFAULT_TTL = 100
DEFAULT_SRC_PORT = 5000
DEFAULT_DST_PORT = 80
MAX_SEGMENT_DATA = 500

# Networks
NET1 = IPv4Network("10.0.1.0/24")
NET2 = IPv4Network("10.0.2.0/24")

# Node addresses (interface IP and MAC)
HOST_A_NAME = "Host A"
HOST_A_IP = "10.0.1.10"
HOST_A_MAC = "AA:AA:AA:AA:AA:AA"

ROUTER_NAME = "Router R1"
R1_IF1_IP = "10.0.1.1"
R1_IF1_MAC = "BB:BB:BB:BB:BB:BB"
R1_IF2_IP = "10.0.2.1"
R1_IF2_MAC = "CC:CC:CC:CC:CC:CC"

HOST_B_NAME = "Host B"
HOST_B_IP = "10.0.2.20"
HOST_B_MAC = "DD:DD:DD:DD:DD:DD"

# Initial neighbour resolution for next-hop gateways
ARP_SEED_HOST_A = {R1_IF1_IP: R1_IF1_MAC}
ARP_SEED_HOST_B = {R1_IF2_IP: R1_IF2_MAC}


@dataclass(frozen=True)
class RoutingEntry:
    """One routing-table row."""
    dest_network: IPv4Network
    next_hop_ip: Optional[str]
    outgoing_interface: str


# Host A: Net1 on-link; Net2 via default gateway R1 (10.0.1.1)
ROUTING_TABLE_HOST_A = (
    RoutingEntry(NET1, None, "eth0"),
    RoutingEntry(NET2, R1_IF1_IP, "eth0"),
)

# Host B: Net2 on-link; Net1 via R1 (10.0.2.1)
ROUTING_TABLE_HOST_B = (
    RoutingEntry(NET2, None, "eth0"),
    RoutingEntry(NET1, R1_IF2_IP, "eth0"),
)

# Router R1: both subnets attached
ROUTING_TABLE_R1 = (
    RoutingEntry(NET1, None, "if1"),
    RoutingEntry(NET2, None, "if2"),
)


def lookup_route(dest_ip, entries):
    """
    Return the routing-table row that best matches dest_ip (longest prefix).
    """
    addr = IPv4Address(dest_ip)
    best = None
    best_len = -1
    for e in entries:
        if addr in e.dest_network and e.dest_network.prefixlen >= best_len:
            best = e
            best_len = e.dest_network.prefixlen
    return best
