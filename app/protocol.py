"""
Protocol data structures and binary layouts for Layers 2–4.

This module is intentionally free of simulation logic: it only defines how fields
map to bytes for encapsulation/decapsulation. Wire format uses network byte order
(big-endian) for multi-byte numeric fields.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from config import IP_PROTOCOL_UDP

# --- Layout sizes ------------------------------------------------------------------

MAC_LEN: Final[int] = 6
ETH_HEADER_LEN: Final[int] = MAC_LEN + MAC_LEN + 2

IP_HEADER_LEN: Final[int] = 4 + 4 + 1 + 1 + 2  # src, dst, ttl, proto, total_length

UDP_HEADER_LEN: Final[int] = 2 + 2 + 2 + 2 + 1 + 1  # ports, length, checksum, type, seq

SEGMENT_TYPE_DATA: Final[int] = 0
SEGMENT_TYPE_ACK: Final[int] = 1


def mac_to_bytes(mac: str) -> bytes:
    """Parse ``'AA:BB:...'`` into six octets."""
    parts = mac.split(":")
    if len(parts) != MAC_LEN:
        raise ValueError(f"Invalid MAC address: {mac!r}")
    return bytes(int(p, 16) for p in parts)


def mac_from_bytes(data: bytes) -> str:
    """Format six octets as ``'AA:BB:...'``."""
    if len(data) != MAC_LEN:
        raise ValueError("MAC must be 6 bytes")
    return ":".join(f"{b:02X}" for b in data)


def ip_to_bytes(ip: str) -> bytes:
    """Encode dotted IPv4 string to four octets."""
    octets = [int(x) for x in ip.split(".")]
    if len(octets) != 4 or any(o < 0 or o > 255 for o in octets):
        raise ValueError(f"Invalid IPv4 address: {ip!r}")
    return bytes(octets)


def ip_from_bytes(data: bytes) -> str:
    """Decode four octets to dotted IPv4 string."""
    if len(data) != 4:
        raise ValueError("IPv4 address must be 4 bytes")
    return ".".join(str(b) for b in data)


def _ones_complement_sum(data: bytes) -> int:
    """16-bit one's complement addition over two-byte chunks (padding with zero)."""
    if len(data) % 2 == 1:
        data = data + b"\x00"
    total = 0
    for i in range(0, len(data), 2):
        word = (data[i] << 8) + data[i + 1]
        total += word
        total = (total & 0xFFFF) + (total >> 16)
    return total & 0xFFFF


def compute_udp_like_checksum(segment_without_checksum: bytes) -> int:
    """
    Compute a 16-bit checksum for the UDP-like segment.

    The checksum field in the segment must be zero when this runs. This follows a
    minimal Internet-style one's complement sum; replace with the assignment's
    exact algorithm if your unit tests require a different bit pattern.
    """
    return _ones_complement_sum(segment_without_checksum) ^ 0xFFFF


@dataclass
class UDPSegment:
    """Transport-layer segment (UDP-like with DATA/ACK and sequence number)."""

    src_port: int
    dst_port: int
    segment_type: int
    sequence_number: int
    data: bytes

    def total_length(self) -> int:
        """Return header + application data length in bytes."""
        return UDP_HEADER_LEN + len(self.data)

    def to_bytes(self) -> bytes:
        """Serialize segment; checksum covers header (checksum field zero) + data."""
        length = self.total_length()
        header_wo_checksum = (
            self.src_port.to_bytes(2, "big")
            + self.dst_port.to_bytes(2, "big")
            + length.to_bytes(2, "big")
            + b"\x00\x00"
            + bytes([self.segment_type & 0xFF])
            + bytes([self.sequence_number & 0xFF])
        )
        body = header_wo_checksum + self.data
        cksum = compute_udp_like_checksum(body)
        return (
            self.src_port.to_bytes(2, "big")
            + self.dst_port.to_bytes(2, "big")
            + length.to_bytes(2, "big")
            + cksum.to_bytes(2, "big")
            + bytes([self.segment_type & 0xFF])
            + bytes([self.sequence_number & 0xFF])
            + self.data
        )

    @classmethod
    def from_bytes(cls, raw: bytes) -> UDPSegment:
        """Parse a segment from bytes."""
        if len(raw) < UDP_HEADER_LEN:
            raise ValueError("Segment too short")
        seg_len = int.from_bytes(raw[4:6], "big")
        if seg_len > len(raw):
            raise ValueError("Segment length field exceeds buffer")
        src_port = int.from_bytes(raw[0:2], "big")
        dst_port = int.from_bytes(raw[2:4], "big")
        seg_type = raw[8]
        seq = raw[9]
        data = raw[10:seg_len] if seg_len > UDP_HEADER_LEN else b""
        return cls(
            src_port=src_port,
            dst_port=dst_port,
            segment_type=seg_type,
            sequence_number=seq,
            data=data,
        )

    @staticmethod
    def checksum_ok(raw: bytes) -> bool:
        """Validate one's-complement checksum over an on-wire segment (checksum field zeroed)."""
        if len(raw) < UDP_HEADER_LEN:
            return False
        zeroed = raw[:6] + b"\x00\x00" + raw[8:]
        return _ones_complement_sum(zeroed) == 0xFFFF


@dataclass
class IPPacket:
    """Simplified IPv4-like packet carrying a UDP-like payload."""

    src_ip: str
    dst_ip: str
    ttl: int
    protocol: int
    payload: bytes

    def total_length(self) -> int:
        return IP_HEADER_LEN + len(self.payload)

    def to_bytes(self) -> bytes:
        tl = self.total_length()
        return (
            ip_to_bytes(self.src_ip)
            + ip_to_bytes(self.dst_ip)
            + bytes([self.ttl & 0xFF])
            + bytes([self.protocol & 0xFF])
            + tl.to_bytes(2, "big")
            + self.payload
        )

    @classmethod
    def from_bytes(cls, raw: bytes) -> IPPacket:
        if len(raw) < IP_HEADER_LEN:
            raise ValueError("IP packet too short")
        src = ip_from_bytes(raw[0:4])
        dst = ip_from_bytes(raw[4:8])
        ttl = raw[8]
        proto = raw[9]
        total_len = int.from_bytes(raw[10:12], "big")
        payload = raw[12:total_len]
        return cls(src_ip=src, dst_ip=dst, ttl=ttl, protocol=proto, payload=payload)


@dataclass
class EthernetFrame:
    """Ethernet-like frame carrying an IPv4-like packet as payload."""

    dst_mac: str
    src_mac: str
    ether_type: int
    payload: bytes

    def to_bytes(self) -> bytes:
        return (
            mac_to_bytes(self.dst_mac)
            + mac_to_bytes(self.src_mac)
            + self.ether_type.to_bytes(2, "big")
            + self.payload
        )

    @classmethod
    def from_bytes(cls, raw: bytes) -> EthernetFrame:
        if len(raw) < ETH_HEADER_LEN:
            raise ValueError("Frame too short")
        dst = mac_from_bytes(raw[0:6])
        src = mac_from_bytes(raw[6:12])
        etype = int.from_bytes(raw[12:14], "big")
        payload = raw[14:]
        return cls(dst_mac=dst, src_mac=src, ether_type=etype, payload=payload)


def build_ipv4_udp_stack(segment: UDPSegment, src_ip: str, dst_ip: str, ttl: int) -> bytes:
    """Helper: segment → IP packet bytes → Ethernet payload is only IP bytes here."""
    ip = IPPacket(
        src_ip=src_ip,
        dst_ip=dst_ip,
        ttl=ttl,
        protocol=IP_PROTOCOL_UDP,
        payload=segment.to_bytes(),
    )
    return ip.to_bytes()
