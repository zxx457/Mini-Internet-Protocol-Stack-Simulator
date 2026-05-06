"""
CITS3002 — Mini Internet Protocol Stack Simulator (scaffold entry point).

Run from this directory:

    python main.py <message_size_bytes>

The simulator is logical only (no sockets). Flesh out ``devices.Host`` and
``devices.Router`` to match the required log output in the project brief.
"""

from __future__ import annotations

import sys

from config import HOST_B_IP
from devices import build_topology


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python main.py <message_size_bytes>")
        return 1
    try:
        size = int(sys.argv[1])
    except ValueError:
        print("message_size_bytes must be an integer")
        return 1
    if size < 0:
        print("message size must be non-negative")
        return 1

    _sim, host_a, _router, _host_b = build_topology()

    # Example application payload (replace with your own pattern if desired)
    payload = bytes((i % 256) for i in range(size))

    # Once ``send_application_data`` is implemented, uncomment:
    # host_a.send_application_data(HOST_B_IP, payload)

    print(
        f"Topology ready; generated {len(payload)}-byte payload for destination {HOST_B_IP}. "
        "Implement Host.send_application_data and layer handlers, then invoke send here."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
