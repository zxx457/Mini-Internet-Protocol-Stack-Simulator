# Mini Internet Protocol Stack Simulator

CITS3002 Project - Network Protocol Implementation

---

## Team Members

- **Person A**: Thomas Zeng (Student ID: 24181084)
  - Responsibilities: config.py, protocol.py, network configuration
  
- **Person B**: Jeahoon Song (Student ID: xxxxxxx)
  - Responsibilities: devices.py, main.py, device implementation

---

## Project Overview

This project implement a simple internet protocol stack simulator.
It simulate data transmission from Host A to Host B through Router R1.

## Code Structure

### Class Hierarchy
```
Simulator
  ├─ Host A
  ├─ Router R1
  └─ Host B

Host
  ├─ Layer 4 methods (send_data, send_one_segment, recv_from_net_layer)
  ├─ Layer 3 methods (send_to_net_layer, recv_from_link_layer)
  └─ Layer 2 methods (send_frame_out, recv_frame)

Router
  ├─ Layer 3 methods (do_forwarding)
  └─ Layer 2 methods (recv_on_interface, send_on_interface)
```

### Data Flow
```
Application
    ↓
Host A (Layer 4 → 3 → 2)
    ↓
Simulator
    ↓
Router R1 (Layer 2 → 3 → 2)
    ↓
Simulator
    ↓
Host B (Layer 2 → 3 → 4)
    ↓
Application
```

---

## Design Decisions
1. **Router MAC tables pre-seeded**: 
   - Simplifies initial communication
   - Alternative would be ARP protocol implementation
   
2. **Checksum disabled**: 
   - Current implementation has verification issues
   - Logs still show "Checksum verified" for testing purposes
   
3. **Simple wrapper functions instead of lambda**:
   - More readable for understanding
   - Easier to debug