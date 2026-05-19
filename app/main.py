# CITS3002 Project - Network Simulator

import sys
from config import HOST_B_IP
from devices import make_network


def main():
    # Check arguments
    if len(sys.argv) != 2:
        print("Usage: python main.py <message_size>")
        return 1
    
    try:
        size = int(sys.argv[1])
    except:
        print("Error: message size must be integer")
        return 1
    
    if size < 0:
        print("Error: message size must be positive")
        return 1
    
    # Build network
    sim, host_a, router, host_b = make_network()
    
    # Make message
    message = bytes((i % 256) for i in range(size))
    
    # Send data from Host A to Host B
    host_a.send_data(HOST_B_IP, message)
    
    print("\n=== Transmission Complete ===")
    return 0


if __name__ == "__main__":
    exit(main())
