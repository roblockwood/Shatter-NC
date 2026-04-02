#!/usr/bin/env python3
"""Test script for telnet client connection and data loading."""
import asyncio
import sys
import logging
from pathlib import Path

# Prevent pytest from collecting this script as a test module.
__test__ = False

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging to show INFO level messages
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)

from app.clients.telnet_client import CNCTelnetClient


async def test_telnet_connection(ip_address: str, port: int = 10000):
    """Test telnet connection and load MEM file."""
    print(f"Testing telnet connection to {ip_address}:{port}")
    print("=" * 60)
    
    client = CNCTelnetClient(ip_address=ip_address, port=port)
    
    try:
        # Connect for data loading
        print("\n1. Connecting...")
        connected = await client.connect()
        if not connected:
            print("   ❌ Failed to connect")
            return
        
        print("   ✅ Connected successfully!")
        
        # Load MEM file first (most reliable)
        print("\n2. Loading MEM file (memory/program information)...")
        print("   Command: LOD MEM")
        mem_data = await client.get_memory_data(verbose=True)
        if mem_data:
            print(f"   ✅ MEM data loaded successfully")
            print(f"   Data length: {len(mem_data)} bytes")
            print(f"   Raw data:")
            print(f"   {repr(mem_data)}")
            print(f"\n   Formatted data:")
            print(f"   {mem_data}")
        else:
            print("   ❌ Failed to load MEM data")
        
        # Try loading directory listing
        print("\n3. Loading directory listing...")
        print("   Command: LOD DIR")
        dir_data = await client.get_directory_listing(verbose=True)
        if dir_data:
            print(f"   ✅ Directory listing loaded successfully")
            print(f"   Data length: {len(dir_data)} bytes")
            print(f"   First 500 characters:")
            print(f"   {dir_data[:500]}")
        else:
            print("   ❌ Failed to load directory listing")
        
        # Try loading TOLNI1 (tool table)
        print("\n4. Loading TOLNI1 (tool table)...")
        print("   Command: LOD TOLNI1")
        tolni_data = await client.get_tool_table_data(verbose=True)
        if tolni_data:
            print(f"   ✅ TOLNI1 data loaded successfully")
            print(f"   Data length: {len(tolni_data)} bytes")
            print(f"   First 500 characters:")
            print(f"   {tolni_data[:500]}")
        else:
            print("   ❌ Failed to load TOLNI1 data")
        
        await client.disconnect()
        print("\n" + "=" * 60)
        print("✅ Test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        await client.disconnect()


if __name__ == "__main__":
    # Get IP address from command line or use default
    if len(sys.argv) > 1:
        ip_address = sys.argv[1]
    else:
        # Use default IP from reference implementation
        ip_address = "192.168.86.89"
        print(f"No IP provided, using default: {ip_address}")
    
    # Get port from command line or use default
    port = 10000
    if len(sys.argv) > 2:
        port = int(sys.argv[2])
    
    print(f"Testing telnet connection to {ip_address}:{port}\n")
    asyncio.run(test_telnet_connection(ip_address, port))

