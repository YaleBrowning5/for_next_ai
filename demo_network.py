#!/usr/bin/env python3
"""
Demonstration script for the network discovery feature.
Shows how the UDP broadcast and TCP communication work.
"""

import subprocess
import time
import signal
import sys
from pathlib import Path

def print_section(title):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)

def main():
    print_section("Network Discovery Demo Script")
    
    # Get the build directory
    script_dir = Path(__file__).parent.absolute()
    network_example = script_dir / "build" / "network_example"
    
    if not network_example.exists():
        print(f"Error: {network_example} not found.")
        print("Please run 'python build.py' first.")
        return 1
    
    print("\nThis script demonstrates the network discovery feature.")
    print("\nFeatures:")
    print("  ✓ UDP broadcast on port 8866 for device discovery")
    print("  ✓ TCP connection establishment after discovery")
    print("  ✓ JSON message format for communication")
    
    print_section("Starting Test Server")
    print("\nStarting a server instance...")
    print("  Device Name: TestServer")
    print("  TCP Port: 9000")
    print("  Discovery Port: 8866")
    
    # Note: This is a demonstration. For full testing, run the executables
    # in separate terminal windows to see the interactive features.
    
    print("\n" + "-" * 60)
    print("To manually test the discovery feature:")
    print("-" * 60)
    
    print("\n1. Open two terminal windows")
    
    print("\n2. In Terminal 1 (Server):")
    print("   cd " + str(script_dir))
    print("   ./build/network_example")
    print("   Choose option: 1")
    print("   Enter device name: MyServer")
    print("   Enter TCP port: 9000")
    
    print("\n3. In Terminal 2 (Client):")
    print("   cd " + str(script_dir))
    print("   ./build/network_example")
    print("   Choose option: 2")
    print("   Wait for device discovery")
    print("   Select the discovered device")
    print("   Send messages interactively")
    
    print("\n4. Expected Behavior:")
    print("   ✓ Client discovers server via UDP broadcast")
    print("   ✓ Client connects to server via TCP")
    print("   ✓ Messages are exchanged in JSON format")
    print("   ✓ Server echoes received messages")
    
    print_section("Architecture Overview")
    
    print("\nUDP Discovery Protocol:")
    print("  1. Server broadcasts: {type: discovery, device_id: ..., tcp_port: ...}")
    print("  2. Client receives broadcast and extracts IP & port")
    print("  3. Client stores device in registry")
    
    print("\nTCP Communication Protocol:")
    print("  1. Client connects to server's TCP port")
    print("  2. Server sends welcome message")
    print("  3. Client sends: {type: data, content: ...}")
    print("  4. Server responds: {type: response, status: ok, message: ...}")
    
    print_section("Network Ports")
    
    print("\n  UDP Discovery Port: 8866 (hardcoded)")
    print("  TCP Communication Port: Configurable (default: 9000)")
    
    print("\n" + "=" * 60)
    print("Demo script completed!")
    print("See cpp_example/NETWORK_README.md for full documentation.")
    print("=" * 60 + "\n")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
