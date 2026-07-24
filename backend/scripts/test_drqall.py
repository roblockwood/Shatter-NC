#!/usr/bin/env python3
"""Test script for DRQALL command."""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.clients.telnet_client import CNCTelnetClient


async def main():
    ip = "192.168.1.100"
    
    print(f"Testing DRQALL command on {ip}...")
    print("=" * 60)
    
    client = CNCTelnetClient(ip_address=ip)
    
    try:
        # Test connection
        print("\n1. Testing connection...")
        result = await client.test_connection()
        if not result.get("success"):
            print(f"❌ Connection failed: {result.get('error')}")
            return
        print(f"✅ Connection successful (latency: {result.get('latency_ms')}ms)")
        
        # Test DRQALL - Get directory listing
        print("\n2. Testing DRQALL (Request directory of all data)...")
        print("   Command: DRQALL")
        directory_data = await client.get_directory_listing(verbose=True)
        
        if directory_data:
            print(f"✅ Successfully retrieved directory listing")
            print(f"   Data length: {len(directory_data)} bytes")
            print(f"\n   Raw response:")
            print(f"   {repr(directory_data[:200])}")
            print(f"\n   Formatted response (first 500 chars):")
            print(f"   {directory_data[:500]}")
            
            # Parse the directory format using the client's parser
            print(f"\n   Parsed directory entries:")
            entries = await client.parse_directory_listing(directory_data)
            
            if entries:
                print(f"   Found {len(entries)} directory entries:")
                for entry in entries[:20]:  # Show first 20
                    print(f"     {entry['name']:12s}  {entry['size']:>10d} bytes")
                if len(entries) > 20:
                    print(f"     ... and {len(entries) - 20} more entries")
            else:
                print(f"   Could not parse entries")
            
            # Debug: Show raw parsing
            print(f"\n   Debug: Manual parsing of first 5 entries (11 chars each: 8-byte name + 3-byte size):")
            data = directory_data.replace('\n', '').replace('\r', '').strip()
            for i in range(min(5, len(data) // 11)):
                start = i * 11
                end = start + 11
                entry = data[start:end]
                name = entry[0:8]
                size = entry[8:11]
                print(f"     Entry {i+1}:")
                print(f"       Raw: {repr(entry)}")
                print(f"       Name (8): {repr(name)} -> '{name.rstrip()}'")
                print(f"       Size (3): {repr(size)} -> '{size.strip()}' -> int={int(size.strip()) if size.strip().isdigit() else 'N/A'}")
        else:
            print("❌ Failed to get directory listing")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.disconnect()
        print("\n" + "=" * 60)
        print("Test completed.")


if __name__ == "__main__":
    asyncio.run(main())

