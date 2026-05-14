"""
Fixed topology parameters, addressing, and routing tables for the simulator.
Values match the CITS3002 project specification.
"""
from dataclasses import dataclass
from ipaddress import IPv4Address, IPv4Network
from typing import Final, Optional

# --- Ethernet / IP / UDP constants -------------------------------------------------
ETHERTYPE_IPV4: Final[int] = 0x0800
IP_PROTOCOL_UDP: Final[int] = 17
DEFAULT_TTL: Final[int] = 100
DEFAULT_SRC_PORT: Final[int] = 5000
DEFAULT_DST_PORT: Final[int] = 80
MAX_SEGMENT_DATA: Final[int] = 500

# --- Networks ----------------------------------------------------------------------
NET1: Final[IPv4Network] = IPv4Network("10.0.1.0/24")
NET2: Final[IPv4Network] = IPv4Network("10.0.2.0/24")

# --- Node addresses (interface IP and MAC) --------------------------------------
HOST_A_NAME: Final[str] = "Host A"
HOST_A_IP: Final[str] = "10.0.1.10"
HOST_A_MAC: Final[str] = "AA:AA:AA:AA:AA:AA"

ROUTER_NAME: Final[str] = "Router R1"
R1_IF1_IP: Final[str] = "10.0.1.1"
R1_IF1_MAC: Final[str] = "BB:BB:BB:BB:BB:BB"
R1_IF2_IP: Final[str] = "10.0.2.1"
R1_IF2_MAC: Final[str] = "CC:CC:CC:CC:CC:CC"

HOST_B_NAME: Final[str] = "Host B"
HOST_B_IP: Final[str] = "10.0.2.20"
HOST_B_MAC: Final[str] = "DD:DD:DD:DD:DD:DD"

# Initial neighbour resolution for next-hop gateways
ARP_SEED_HOST_A: Final[dict[str, str]] = {R1_IF1_IP: R1_IF1_MAC}
ARP_SEED_HOST_B: Final[dict[str, str]] = {R1_IF2_IP: R1_IF2_MAC}


@dataclass(frozen=True)
class RoutingEntry:
    """One routing-table row."""
    dest_network: IPv4Network
    next_hop_ip: Optional[str]
    outgoing_interface: str


# Host A: Net1 on-link; Net2 via default gateway R1 (10.0.1.1)
ROUTING_TABLE_HOST_A: Final[tuple[RoutingEntry, ...]] = (
    RoutingEntry(NET1, None, "eth0"),
    RoutingEntry(NET2, R1_IF1_IP, "eth0"),
)

# Host B: Net2 on-link; Net1 via R1 (10.0.2.1)
ROUTING_TABLE_HOST_B: Final[tuple[RoutingEntry, ...]] = (
    RoutingEntry(NET2, None, "eth0"),
    RoutingEntry(NET1, R1_IF2_IP, "eth0"),
)

# Router R1: both subnets attached
ROUTING_TABLE_R1: Final[tuple[RoutingEntry, ...]] = (
    RoutingEntry(NET1, None, "if1"),
    RoutingEntry(NET2, None, "if2"),
)


def longest_prefix_match(dest_ip: str, entries: tuple[RoutingEntry, ...]) -> Optional[RoutingEntry]:
    """
    Return the most specific RoutingEntry whose dest_network contains dest_ip.
    """
    addr = IPv4Address(dest_ip)
    best: Optional[RoutingEntry] = None
    best_len = -1
    for e in entries:
        if addr in e.dest_network and e.dest_network.prefixlen >= best_len:
            best = e
            best_len = e.dest_network.prefixlen
    return best
