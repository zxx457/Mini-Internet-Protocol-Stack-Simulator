# CITS3002 — Mini Internet Protocol Stack Simulator (scaffold)

This repository follows the required layout:

| File | Purpose |
|------|---------|
| `main.py` | CLI entry (`python main.py <size>`); wires topology and starts the transfer |
| `protocol.py` | Layer 2–4 binary layouts (`EthernetFrame`, `IPPacket`, `UDPSegment`) |
| `devices.py` | `Host`, `Router`, `Simulator`, and `build_topology()` |
| `config.py` | Fixed IPs, MACs, routing seeds, limits |

## Run

```bash
python main.py 10
```

## Implementation notes

1. **Layers**: Implement `Host` / `Router` methods marked `NotImplementedError`, matching the assignment log strings.
2. **Routing**: Use `longest_prefix_match()` and resolve `next_hop_ip` (`None` ⇒ destination host IP on-link).
3. **rdt2.2**: Stop-and-wait with alternating sequence bits; segment payloads over `MAX_SEGMENT_DATA` bytes.
4. **Standards**: Only the Python standard library; no `socket` or third-party packages.

Replace this README with your own brief design summary before submission.
